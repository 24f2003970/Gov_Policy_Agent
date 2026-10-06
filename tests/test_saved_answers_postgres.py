"""Real PostgreSQL bookmark ownership, concurrency and current source gates."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from copy import deepcopy
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import pytest
from app.answer_models import AnswerRun, SavedAnswer
from app.document_models import Document
from app.models import User
from app.auth import now
from app.answer_worker import Worker
from test_answers_postgres import HostDouble, NoGeneration, EmptyRetriever
from app.grounding import GroundedOutput, final_result
from test_auth_postgres import postgres, ORIGIN, REG, auth_header
from test_documents_postgres import docs
from test_retrieval_postgres import encoder
from test_citations_postgres import prepare


def seed(docs, encoder, tmp_path, count=1):
    _,v,_,passages,good=prepare(docs,encoder,tmp_path)
    client,_,engine,headers=docs
    result=final_result(GroundedOutput(status='answered',language='en',claims=[good],limitations=[]),passages,'en')
    with Session(engine) as db:
        user=db.scalar(select(User));user.role='user'
        runs=[AnswerRun(user_id=user.id,question=f'Synthetic historical question {i}',language='en',filters={},state='done',result=deepcopy(result),sources=passages,model={}) for i in range(count)]
        db.add_all(runs);db.commit();ids=[str(r.id) for r in runs]
    return client,engine,headers,v,ids


def test_bookmark_private_idempotent_concurrent_and_unassessed(docs,encoder,tmp_path):
    client,engine,h,v,ids=seed(docs,encoder,tmp_path)
    rid=ids[0];path=f'/ask/history/{rid}/saved'
    assert client.get('/ask/saved').status_code==401
    assert client.put(path).status_code in (401,403)
    assert client.put(path,headers={k:x for k,x in h.items() if k!='X-CSRF-Protection'}).status_code==403
    preflight=client.options(path,headers={'Origin':ORIGIN['Origin'],'Access-Control-Request-Method':'PUT','Access-Control-Request-Headers':'authorization,x-csrf-protection'})
    assert preflight.status_code==200 and 'DELETE' in preflight.headers['access-control-allow-methods']
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses=list(pool.map(lambda _:client.put(path,headers=h),range(4)))
    assert all(r.status_code==200 and r.json()['saved'] for r in responses)
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(SavedAnswer))==1
        saved=db.scalar(select(SavedAnswer));timestamp=saved.created_at
        snapshot=deepcopy(db.get(AnswerRun,UUID(rid)).result)
    assert client.put(path,headers=h).json()['evidence_quality']['status']=='not_evaluated'
    with Session(engine) as db:
        assert db.scalar(select(SavedAnswer)).created_at==timestamp
        assert db.get(AnswerRun,UUID(rid)).result==snapshot
    assert set(client.get('/ask/saved',headers=h).json()['items'][0]).isdisjoint({'result','sources','citations','evidence_quality'})
    other={**REG,'email':'bookmark-other@example.com','username':'bookmark_other'}
    assert client.post('/auth/register',headers=ORIGIN,json=other).status_code==201
    token=client.post('/auth/login',headers=ORIGIN,json={'email':other['email'],'password':other['password']}).json()['access_token']
    oh={**ORIGIN,**auth_header(token)}
    assert client.get('/ask/saved',headers=oh).json()['total']==0
    for method in (client.get,client.put,client.delete):
        assert method(path if method!=client.get else f'/ask/history/{rid}',headers=oh).status_code==404
    assert client.get('/ask/history',headers=oh).json()['total']==0
    with Session(engine) as db:
        other_id=db.scalar(select(User.id).where(User.username==other['username']))
        db.add(SavedAnswer(user_id=other_id,run_id=UUID(rid)))
        with pytest.raises(IntegrityError):db.commit()
        db.rollback()
    assert client.delete(path,headers={k:x for k,x in h.items() if k!='X-CSRF-Protection'}).status_code==403
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert all(r.status_code==200 for r in pool.map(lambda _:client.delete(path,headers=h),range(4)))
    assert client.get('/ask/saved',headers=h).json()['total']==0
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert all(r.status_code==200 for r in pool.map(lambda f:f(path,headers=h),(client.put,client.delete)))
    assert client.delete(path,headers=h).json()['saved'] is False
    assert client.put(path,headers=h).json()['saved'] is True


def test_pagination_revocation_and_retention_cascade(docs,encoder,tmp_path):
    client,engine,h,v,ids=seed(docs,encoder,tmp_path,21)
    for rid in ids:assert client.put(f'/ask/history/{rid}/saved',headers=h).status_code==200
    first=client.get('/ask/saved',headers=h).json();second=client.get('/ask/saved?page=2',headers=h).json()
    assert first['total']==21 and len(first['items'])==20 and first['has_next']
    assert len(second['items'])==1 and not second['has_next']
    assert len({r['id'] for r in first['items']+second['items']})==21
    assert client.get('/ask/saved?page=0',headers=h).status_code==422
    with Session(engine) as db:
        db.get(Document,UUID(v['document_id'])).archived_at=now();db.commit()
    assert all(not r['available'] for r in client.get('/ask/saved',headers=h).json()['items'])
    rid=ids[0];path=f'/ask/history/{rid}/saved'
    detail=client.get(f'/ask/history/{rid}',headers=h).json()
    assert detail['saved'] and detail['source_access_withheld'] and not detail['can_save']
    assert detail['result']['claims']==[] and all(c['quote'] is None for c in detail['citations'])
    assert client.put(path,headers=h).status_code==409
    assert client.delete(path,headers=h).status_code==200
    with Session(engine) as db:
        run=db.get(AnswerRun,UUID(ids[1]));run.created_at=now()-timedelta(days=31);db.commit()
    assert client.get('/ask/saved',headers=h).json()['total']==19
    assert client.put(f'/ask/history/{ids[1]}/saved',headers=h).status_code==409
    with Session(engine) as db:uid=db.get(AnswerRun,UUID(ids[1])).user_id
    Worker(docs[1],engine,HostDouble(),generator=NoGeneration(),retriever=EmptyRetriever()).recover()
    with Session(engine) as db:
        assert db.get(AnswerRun,UUID(ids[1])) is None
        assert db.get(SavedAnswer,(uid,UUID(ids[1]))) is None
    assert client.get(f'/ask/history/{ids[1]}',headers=h).status_code==404


def test_unsaveable_states(docs,encoder,tmp_path):
    client,engine,h,_,ids=seed(docs,encoder,tmp_path)
    with Session(engine) as db:
        r=db.get(AnswerRun,UUID(ids[0]));r.result={**r.result,'status':'partial'};db.commit()
    assert client.put(f'/ask/history/{ids[0]}/saved',headers=h).status_code==200
    assert client.delete(f'/ask/history/{ids[0]}/saved',headers=h).status_code==200
    for state,status in [('error','answered'),('queued','answered'),('done','needs_clarification'),('done','insufficient_evidence')]:
        with Session(engine) as db:
            run=db.get(AnswerRun,UUID(ids[0]));run.state=state;run.result={**run.result,'status':status};db.commit()
        assert client.put(f'/ask/history/{ids[0]}/saved',headers=h).status_code==409
    with Session(engine) as db:
        run=db.get(AnswerRun,UUID(ids[0]));run.result={**run.result,'status':'answered','claims':[]};db.commit()
    assert client.put(f'/ask/history/{ids[0]}/saved',headers=h).status_code==409
