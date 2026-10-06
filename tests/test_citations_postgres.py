"""Real dedicated SQL, exact spans and current access; judge doubles isolate pipeline behavior."""
import asyncio
from copy import deepcopy
from uuid import UUID
import json
import pytest
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.answer_models import AnswerRun
from app.citation_models import AnswerClaim,ClaimCitation
from app.citations import context_for,persist_claims
from app.grounding import Claim,Evidence,GroundedOutput,final_result,RagError
from app.models import User
from app.support import SupportVerifier
from app.vector_index import queue
from app.document_models import Document,ExtractedPage
from app.auth import now
from test_auth_postgres import postgres,ORIGIN,REG
from test_documents_postgres import docs
from test_retrieval_postgres import encoder,indexed
from test_answers_postgres import HostDouble
from app.answer_worker import Worker
from app.grounding import quote_options
from app.evidence_quality import assess


class Judge:
    def judge_budget(self,*args):return 'synthetic',10
    async def judge(self,*args):return json.dumps({'outcome':'supported_by_check','reason':'direct_support','evidence_ids':self.ids}),{}


def prepare(docs,encoder,tmp_path):
    runtime,v,jid=indexed(docs,encoder,tmp_path)
    passages=runtime.search('How much money do farmers receive every year?')['items']
    p=passages[0]
    evidence=Evidence(id=p['chunk_id'],quote=p['text'],quote_start_offset=p['start_offset'],quote_end_offset=p['end_offset'])
    good=Claim(text='Farmers receive annual financial assistance of six thousand rupees.',evidence=[evidence])
    return runtime,v,jid,passages,good


def test_filter_persistence_legacy_owner_and_revoked_history(docs,encoder,tmp_path):
    runtime,v,jid,passages,good=prepare(docs,encoder,tmp_path)
    client,_,engine,headers=docs
    judge=Judge();judge.ids=[passages[0]['chunk_id']]
    bad=Claim(text='Farmers receive financial assistance of Rs 9,000 monthly.',evidence=good.evidence)
    output=GroundedOutput(status='answered',language='en',claims=[good,bad],limitations=[])
    checked,records,metrics=asyncio.run(SupportVerifier(engine,judge).evaluate(output,passages,str(jid)))
    assert checked.status=='partial' and checked.claims==[good] and metrics['retained_claims']==1
    with Session(engine) as db:
        user=db.scalar(select(User));user.role='user'
        run=AnswerRun(user_id=user.id,question='Synthetic historical source?',language='en',filters={},state='done',
            result=final_result(checked,passages,'en'),sources=passages,model={'index_generation':str(jid),'digest':'synthetic-judge-double'})
        legacy=AnswerRun(user_id=user.id,question='Legacy fixture?',language='en',filters={},state='done',
            result=final_result(GroundedOutput(status='answered',language='en',claims=[good],limitations=[]),passages,'en'),sources=passages,model={})
        db.add_all([run,legacy]);db.flush();persist_claims(db,run,records)
        run.finished_at=now();run.evidence_quality=assess(run,records);db.commit()
        rid,lid=str(run.id),str(legacy.id);snapshot=deepcopy(legacy.result)
        quality_snapshot=deepcopy(run.evidence_quality)
        assert db.scalar(select(func.count()).select_from(AnswerClaim).where(AnswerClaim.run_id==run.id))==2
    detail=client.get('/ask/history/'+rid,headers=headers).json()
    assert detail['result']['status']=='partial' and len(detail['result']['claims'])==1
    assert detail['evidence_quality']['schema_version']==1
    assert detail['evidence_quality']['components']['citation_coverage']['value']==1
    assert detail['evidence_quality']['counts']['rejected_records']==1
    assert detail['evidence_quality']['source_references'][0]['review']['review_id']
    assert '9,000' not in json.dumps(detail)
    citation=detail['citations'][0];cid=citation['citation_id']
    assert citation['support']['outcome']=='supported_by_check' and citation['provenance']['status']=='valid'
    path=f'/ask/history/{rid}/citations/{cid}/text'
    assert client.get(path,headers=headers).status_code==200
    assert client.get(f"/admin/documents/versions/{v['id']}/original",headers=headers).status_code==403
    old=client.get('/ask/history/'+lid,headers=headers).json()
    assert old['citations'][0]['support']['outcome']=='not_evaluated'
    assert old['evidence_quality']['status']=='not_evaluated'
    with Session(engine) as db:
        assert db.get(AnswerRun,UUID(lid)).result==snapshot
        assert db.scalar(select(func.count()).select_from(AnswerClaim).where(AnswerClaim.run_id==UUID(lid)))==0
        queue(db)
    assert runtime.run_once()  # New active index must not rewrite historical references.
    assert client.get(path,headers=headers).status_code==200
    assert client.get('/ask/history/'+rid,headers=headers).json()['citations'][0]['citation_id']==cid
    assert client.get('/ask/history/'+rid,headers=headers).json()['evidence_quality']==quality_snapshot
    with Session(engine) as db:
        doc=db.get(Document,UUID(v['document_id']));doc.archived_at=now();db.commit()
    revoked=client.get('/ask/history/'+rid,headers=headers).json()
    assert revoked['source_access_withheld'] and revoked['result']['claims']==[]
    assert revoked['evidence_quality']['status']=='source_unavailable'
    assert revoked['evidence_quality']['source_references']==[] and revoked['evidence_quality']['counts']=={}
    assert all(c['value'] is None for c in revoked['evidence_quality']['components'].values())
    assert 'evidence_quality' not in client.get('/ask/history',headers=headers).json()['items'][0]
    assert all(c['quote'] is None and c['claim_text'] is None for c in revoked['citations'])
    assert all(p['text'] is None for p in revoked['sources'])
    assert client.get(path,headers=headers).status_code==403
    with Session(engine) as db:
        assert db.scalar(select(ClaimCitation)).quote==good.evidence[0].quote  # Private audit snapshot preserved.
        assert db.get(AnswerRun,UUID(lid)).result==snapshot
        assert db.get(AnswerRun,UUID(rid)).evidence_quality==quality_snapshot
    client.post('/auth/logout',headers=headers)
    other={**REG,'email':'other@example.com','username':'other_user'}
    client.post('/auth/register',headers=ORIGIN,json=other)
    token=client.post('/auth/login',headers=ORIGIN,json={'email':other['email'],'password':other['password']}).json()['access_token']
    assert client.get(path,headers={'Authorization':'Bearer '+token}).status_code==404
    assert client.get('/ask/history/'+rid,headers={'Authorization':'Bearer '+token}).status_code==404
    assert client.get('/ask/history/'+rid).status_code==401


@pytest.mark.parametrize('change',['archive','review'])
def test_source_changes_during_support_and_invalid_original(docs,encoder,tmp_path,change):
    runtime,v,jid,passages,good=prepare(docs,encoder,tmp_path)
    client,_,engine,headers=docs
    class Changing(Judge):
        async def judge(self,*args):
            if change=='archive':
                with Session(engine) as db:
                    db.get(Document,UUID(v['document_id'])).archived_at=now();db.commit()
            else:
                response=client.post(f"/admin/documents/versions/{v['id']}/reviews",headers=headers,json={
                    'decision':'rejected','reuse_status':'local_reference_only','applicability':'unknown',
                    'reason':'Synthetic revocation during support check only','scope':'Isolated test fixture',
                    'evidence_url':'https://example.gov.in/revoked'})
                assert response.status_code==200
            return await super().judge(*args)
    judge=Changing();judge.ids=[passages[0]['chunk_id']]
    with pytest.raises(RagError,match='source_status_changed'):
        asyncio.run(SupportVerifier(engine,judge).evaluate(GroundedOutput(status='answered',language='en',claims=[good],limitations=[]),passages,str(jid)))
    with Session(engine) as db:
        e=good.evidence[0].model_copy(update={'quote':'Fabricated original quote.'})
        with pytest.raises(RagError,match='citation_provenance_invalid'):context_for(db,e,passages[0])


@pytest.mark.parametrize('error',['verification_unavailable','verification_timeout','verification_invalid_output'])
def test_worker_verifier_failure_publishes_no_claims(docs,encoder,tmp_path,error):
    _,_,jid,passages,good=prepare(docs,encoder,tmp_path)
    client,settings,engine,headers=docs
    class Retrieved:
        async def retrieve(self,*args):return {'items':passages,'generation':str(jid)}
    class Generated:
        manifest={'tag':'isolated-generation-double'}
        def budget(self,*args):return 'synthetic',10,passages,False
        async def generate(self,*args):return json.dumps({'status':'answered','language':'en',
            'claims':[{'text':good.text,'evidence':[{'id':passages[0]['chunk_id'],'quote_id':next(iter(quote_options(passages[0])))}]}],'limitations':[]}),{}
    class Failed:
        async def evaluate(self,*args):raise RagError(error)
    host=HostDouble();worker=Worker(settings,engine,host,generator=Generated(),retriever=Retrieved(),verifier=Failed());worker.recover()
    rid=client.post('/ask',headers=headers,json={'question':'2025 PM-KISAN factsheet annual support'}).json()['id']
    assert asyncio.run(worker.once())
    detail=client.get('/ask/history/'+rid,headers=headers).json()
    assert detail['state']=='error' and detail['error_code']==error and detail['result'] is None and detail['citations']==[]
    assert detail['evidence_quality']['status']=='generation_failed'
    assert detail['evidence_quality']['full_aggregate'] is None and detail['evidence_quality']['source_references']==[]
    assert host.restarts==int(error in ('verification_unavailable','verification_timeout'))


def test_changed_original_withholds_legacy_snapshot(docs,encoder,tmp_path):
    _,_,_,passages,good=prepare(docs,encoder,tmp_path)
    client,_,engine,headers=docs
    with Session(engine) as db:
        user=db.scalar(select(User))
        run=AnswerRun(user_id=user.id,question='Old fixture?',language='en',filters={},state='done',
            result=final_result(GroundedOutput(status='answered',language='en',claims=[good],limitations=[]),passages,'en'),sources=passages,model={})
        db.add(run);db.commit();rid=str(run.id);snapshot=deepcopy(run.result)
        from app.index_models import IndexPassage
        p=db.get(IndexPassage,UUID(passages[0]['chunk_id']));page=db.get(ExtractedPage,p.page_id)
        page.text='Changed synthetic extracted original.';db.commit()
    detail=client.get('/ask/history/'+rid,headers=headers).json()
    assert detail['source_access_withheld'] and detail['result']['claims']==[]
    assert detail['citations'][0]['current_access']['reasons']==['provenance_changed']
    with Session(engine) as db:assert db.get(AnswerRun,UUID(rid)).result==snapshot
