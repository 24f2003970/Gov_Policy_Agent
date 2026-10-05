"""Owned answer state/source changes in dedicated PostgreSQL. Generation doubles isolate failures."""
import asyncio
from datetime import timedelta
import json
from uuid import UUID
import pytest
from sqlalchemy import select,text
from sqlalchemy.orm import Session
from app.answer_models import AnswerRun,AnswerWorker
from app.answer_worker import Worker,validate_sources
from app.auth import now
from app.document_models import Document
from app.models import User
from app.grounding import RagError,quote_options
from test_auth_postgres import postgres,ORIGIN,REG
from test_documents_postgres import docs
from test_retrieval_postgres import encoder,indexed

class HostDouble:
    def __init__(self):self.restarts=0
    def restart(self):self.restarts+=1

class EmptyRetriever:
    async def retrieve(self,*args):return {'status':'empty','items':[]}

class NoGeneration:
    manifest={'tag':'isolated-generation-double'}
    def budget(self,*args):raise AssertionError('Should not generate without evidence')

def test_owned_history_busy_cancel_and_restart_records(docs):
    client,settings,engine,headers=docs
    assert client.get('/ask/history').status_code==401
    assert client.post('/ask',headers=headers,json={'question':'2025 PM-KISAN support'}).status_code==503
    worker=Worker(settings,engine,HostDouble(),generator=NoGeneration(),retriever=EmptyRetriever());worker.recover()
    first=client.post('/ask',headers=headers,json={'question':'What is the orbital period of Neptune?','language':'en'})
    assert first.status_code==202
    rid=first.json()['id']
    assert client.post('/ask',headers=headers,json={'question':'Another request'}).status_code==503
    assert asyncio.run(worker.once())
    detail=client.get('/ask/history/'+rid,headers=headers).json()
    assert detail['state']=='done' and detail['result']['status']=='insufficient_evidence'
    assert detail['result']['trust_score'] is None
    assert client.get('/ask/history',headers=headers).json()['items'][0]['id']==rid
    # New app connection still reads SQL, not process memory.
    with Session(engine) as db:assert db.get(AnswerRun,UUID(rid)).result['status']=='insufficient_evidence'
    queued=client.post('/ask',headers=headers,json={'question':'2025 PM-KISAN support'}).json()['id']
    assert client.post(f'/ask/history/{queued}/cancel',headers=headers).json()['state']=='cancelled'
    client.post('/auth/logout',headers=headers)
    second={**REG,'email':'second@example.com','username':'second_user'}
    assert client.post('/auth/register',headers=ORIGIN,json=second).status_code==201
    login=client.post('/auth/login',headers=ORIGIN,json={'email':second['email'],'password':second['password']}).json()
    other={**ORIGIN,'Authorization':'Bearer '+login['access_token']}
    assert client.get('/ask/history',headers=other).json()['items']==[]
    assert client.get('/ask/history/'+rid,headers=other).status_code==404
    assert client.post('/ask/history/'+rid+'/cancel',headers=other).status_code==404


def test_source_change_during_generation_and_later_history_warning(docs,encoder,tmp_path):
    runtime,version,jid=indexed(docs,encoder,tmp_path)
    client,settings,engine,headers=docs
    passages=runtime.search('How much money do farmers receive every year?')['items']
    class Retrieved:
        async def retrieve(self,*args):return {'items':passages,'generation':str(jid)}
    class ChangesDuringGeneration:
        manifest={'tag':'isolated-generation-double'}
        def budget(self,q,lang,p,repair=None):return 'synthetic',10,p,False
        async def generate(self,*args):
            with Session(engine) as db:
                document=db.get(Document,UUID(version['document_id']));document.archived_at=now();db.commit()
            return json.dumps({'status':'answered','language':'en','claims':[{'text':'The test source describes annual support.',
                'evidence':[{'id':passages[0]['chunk_id'],'quote_id':next(iter(quote_options(passages[0])))}]}],'limitations':[]}),{}
    worker=Worker(settings,engine,HostDouble(),generator=ChangesDuringGeneration(),retriever=Retrieved());worker.recover()
    rid=client.post('/ask',headers=headers,json={'question':'2025 PM-KISAN factsheet annual support'}).json()['id']
    assert asyncio.run(worker.once())
    detail=client.get('/ask/history/'+rid,headers=headers).json()
    assert detail['state']=='error' and detail['error_code']=='source_status_changed' and detail['result'] is None
    with Session(engine) as db:
        record=db.get(AnswerRun,UUID(rid));record.sources=passages;db.commit()
    assert client.get('/ask/history/'+rid,headers=headers).json()['current_source_warnings']


def test_processing_cancellation_timeout_recovery_and_retention(docs,monkeypatch):
    client,settings,engine,headers=docs
    host=HostDouble()
    class SlowRetriever:
        async def retrieve(self,*args):await asyncio.sleep(30)
    worker=Worker(settings,engine,host,generator=NoGeneration(),retriever=SlowRetriever());worker.recover()
    rid=client.post('/ask',headers=headers,json={'question':'2025 PM-KISAN factsheet support'}).json()['id']
    async def cancelled():
        task=asyncio.create_task(worker.once())
        await asyncio.sleep(.1)
        with Session(engine) as db:r=db.get(AnswerRun,UUID(rid));r.cancel_requested=True;db.commit()
        await task
    asyncio.run(cancelled())
    assert host.restarts==1
    assert client.get('/ask/history/'+rid,headers=headers).json()['state']=='cancelled'
    import app.answer_worker as module
    monkeypatch.setattr(module,'DEADLINE_SECONDS',1)
    rid2=client.post('/ask',headers=headers,json={'question':'2025 PM-KISAN factsheet support'}).json()['id']
    assert asyncio.run(worker.once())
    assert client.get('/ask/history/'+rid2,headers=headers).json()['error_code']=='generation_timeout'
    assert host.restarts==2
    with Session(engine) as db:
        r=db.get(AnswerRun,UUID(rid2));r.state='processing';db.commit()
    worker.recover()
    assert client.get('/ask/history/'+rid2,headers=headers).json()['error_code']=='worker_interrupted'
    with Session(engine) as db:r=db.get(AnswerRun,UUID(rid));r.created_at=now()-timedelta(days=31);db.commit()
    worker.recover()
    assert client.get('/ask/history/'+rid,headers=headers).status_code==404
