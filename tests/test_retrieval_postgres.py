"""Real offline model/Chroma and dedicated PostgreSQL; synthetic sources never enter app collections."""
from datetime import date, timedelta
import json
from pathlib import Path
import subprocess
import sys
from uuid import UUID, uuid4
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.auth import now
from app.config import Settings
from app.embedding import Encoder, SPEC
from app.eligibility import eligibility
from app.document_models import Document, DocumentVersion, ExtractedPage, IngestionJob, VersionRelationship
from app.index_models import IndexGeneration, IndexPassage, IndexState, EligibilityReview
from app.ingestion import run_once
from app.vector_index import Runtime, queue
from app.models import User
from test_auth_postgres import postgres
from test_documents_postgres import docs, upload, META


@pytest.fixture(scope='session')
def encoder():
    return Encoder(Settings())  # Explicitly prepared real model required; no mock fallback/download.


def eligible_source(docs, content='PM Kisan provides financial assistance of six thousand rupees every year to farmers in three equal instalments.'):
    client, settings, engine, headers = docs
    version = upload(docs, content.encode('utf-8'), name='synthetic.txt',
        metadata={**META, 'scheme':'Synthetic scheme','document_type':'factsheet'}).json()['version']
    assert run_once(engine, settings)
    assert client.patch(f"/admin/documents/versions/{version['id']}/provenance",headers=headers,
        json={'status':'verified','note':'Synthetic fixture verification only, never official government evidence'}).status_code==200
    assert client.post(f"/admin/documents/versions/{version['id']}/reviews",headers=headers,
        json={'decision':'verified','reuse_status':'permission_recorded','applicability':'historical',
              'reason':'Synthetic fixture rights review for isolated test collection only',
              'evidence_url':'https://example.gov.in/test-terms','scope':'Synthetic test only; never official government evidence'}).status_code==200
    return version


def indexed(docs, encoder, tmp_path):
    version = eligible_source(docs)
    _, settings, engine, _ = docs
    runtime = Runtime(settings,engine,encoder=encoder,vector_dir=tmp_path/'test-vectors')
    with Session(engine) as db: job_id=queue(db).id
    assert runtime.run_once()
    with Session(engine) as db: assert db.get(IndexGeneration,job_id).state=='ready'
    return runtime, version, job_id


def test_real_embeddings_token_limits_and_exact_chunks(encoder):
    q=encoder.encode(['How much annual income support do farmers receive?','किसानों को हर साल कितनी आर्थिक सहायता मिलती है?'],query=True)
    p=encoder.encode(['Farmers receive annual financial assistance of six thousand rupees.','A telescope observes distant galaxies and stars.'])
    import numpy as np
    assert np.array(q).shape==(2,384) and np.allclose(np.linalg.norm(q,axis=1),1,atol=1e-5)
    assert all(np.dot(v,p[0])>np.dot(v,p[1]) for v in q)
    with pytest.raises(ValueError,match='token_limit'): encoder.encode(['किसान '*600],query=True)
    text=('Section 1 Farmers\nकिसानों को आर्थिक सहायता मिलती है। ' * 100)
    chunks=list(encoder.chunks(text));covered=set()
    for c in chunks:
        assert c['text']==text[c['start_offset']:c['end_offset']]
        assert encoder.tokens(c['text'])<=448
        covered.update(range(c['start_offset'],c['end_offset']))
    assert covered==set(range(len(text))) and any(c['continued_clause'] for c in chunks[1:])


def test_real_index_idempotence_and_process_persistence(docs,encoder,tmp_path):
    runtime,v,jid=indexed(docs,encoder,tmp_path)
    with Session(runtime.engine) as db:
        job=db.get(IndexGeneration,jid);collection=runtime.collection(job)
        old=set(collection.get(include=[])['ids'])
        passages=list(db.scalars(select(IndexPassage).where(IndexPassage.generation_id==jid)))
        page=db.get(ExtractedPage,passages[0].page_id)
        assert passages[0].text==page.text[passages[0].start_offset:passages[0].end_offset]
    collection.upsert(ids=list(old),embeddings=encoder.encode([passages[0].text]),metadatas=[{'version_id':v['id']}])
    assert collection.count()==len(old)
    code="import chromadb,sys; c=chromadb.PersistentClient(path=sys.argv[1]); print(c.get_collection(sys.argv[2],embedding_function=None).count())"
    child=subprocess.run([sys.executable,'-c',code,str(tmp_path/'test-vectors'),collection.name],capture_output=True,text=True,timeout=45)
    assert child.returncode==0 and child.stdout.strip()==str(len(old))
    result=runtime.search('How much money do farmers receive every year?')
    assert result['status']=='results' and result['items'][0]['version_id']==v['id']
    assert runtime.search('किसानों को प्रति वर्ष कितनी सहायता मिलती है?')['status']=='results'


def test_filters_archive_ineligible_partial_superseded(docs,encoder,tmp_path):
    runtime,v,jid=indexed(docs,encoder,tmp_path)
    client,_,engine,headers=docs
    question='How much money do farmers receive every year?'
    assert runtime.search(question,scheme='Unknown scheme')['status']=='empty'
    assert runtime.search(question,issuer='No such ministry')['status']=='empty'
    assert runtime.search(question,document_type='unrelated')['status']=='empty'
    assert runtime.search(question,published_after=date(2025,1,1))['status']=='empty'
    assert runtime.search(question,published_after=date(2025,1,1),unknown_dates='include')['status']=='results'
    client.patch(f"/admin/documents/{v['document_id']}/archive",headers=headers,json={'archived':True})
    assert runtime.search(question)['status']=='empty'
    client.patch(f"/admin/documents/{v['document_id']}/archive",headers=headers,json={'archived':False})
    with Session(engine) as db:
        job=db.scalar(select(IngestionJob).where(IngestionJob.version_id==UUID(v['id'])))
        job.state='partial';db.commit()
    assert runtime.search(question)['status']=='empty'
    with Session(engine) as db:
        job=db.scalar(select(IngestionJob).where(IngestionJob.version_id==UUID(v['id'])))
        job.state='completed'
        db.commit()
    other=eligible_source(docs,'Synthetic newer source: annual financial support for farmers is described in another edition.')
    assert client.post(f"/admin/documents/versions/{other['id']}/relationships",headers=headers,
        json={'to_version_id':v['id'],'kind':'supersedes','evidence_url':'https://example.gov.in/supersedes','scope_note':'Synthetic scope only, explicitly verified supersession'}).status_code==201
    assert runtime.search(question)['status']=='empty'


def test_audit_reviews_immutable_and_immediate_revocation(docs,encoder,tmp_path):
    runtime,v,jid=indexed(docs,encoder,tmp_path)
    client,_,engine,headers=docs
    body={'decision':'rejected','reuse_status':'local_reference_only','applicability':'unknown',
        'reason':'Synthetic review correction with explicit evidence reference', 'scope':'Synthetic test scope; no official publication',
        'evidence_url':'https://example.gov.in/terms'}
    r=client.post(f"/admin/documents/versions/{v['id']}/reviews",headers=headers,json=body)
    assert r.status_code==200 and not r.json()['eligible']
    assert runtime.search('How much money do farmers receive?')['status']=='empty'
    history=client.get(f"/admin/documents/versions/{v['id']}/reviews",headers=headers).json()['items']
    assert [review['decision'] for review in history]==['rejected','verified']
    with engine.begin() as c:
        with pytest.raises(DBAPIError):c.execute(text("UPDATE eligibility_reviews SET decision='verified'"))


def test_collection_mismatch_reconciliation_and_empty(docs,encoder,tmp_path):
    runtime,v,jid=indexed(docs,encoder,tmp_path)
    with Session(runtime.engine) as db:collection=runtime.collection(db.get(IndexGeneration,jid))
    with Session(runtime.engine) as db:
        job=db.get(IndexGeneration,jid);job.spec={**SPEC,'revision':'wrong'};db.commit()
    with pytest.raises(ValueError,match='index_model_mismatch'):runtime.search('Farmers annual financial assistance')
    with Session(runtime.engine) as db:
        job=db.get(IndexGeneration,jid);job.spec=SPEC;db.commit()
    collection.upsert(ids=['stale-test-vector'],embeddings=encoder.encode(['Synthetic stale passage']),metadatas=[{'version_id':v['id']}])
    assert runtime.reconcile()['removed_stale']==1
    collection.delete(ids=collection.get(include=[])['ids'])
    assert runtime.reconcile()['missing']>0
    assert runtime.search('Farmers annual financial assistance')['status']=='unavailable'
    with Session(runtime.engine) as db:
        document=db.get(Document,UUID(v['document_id']));document.archived_at=now();db.commit()
        empty=queue(db).id
    assert runtime.run_once()
    with Session(runtime.engine) as db:assert db.get(IndexGeneration,empty).total==0
    assert runtime.search('Farmers annual financial assistance')['status']=='empty'
    collection.modify(metadata={'spec':'wrong'})
    with Session(runtime.engine) as db:
        with pytest.raises(ValueError,match='collection_model_mismatch'):runtime.collection(db.get(IndexGeneration,jid))


def test_failed_generation_and_lease_restart_recovery(docs,encoder,tmp_path):
    runtime,v,old=indexed(docs,encoder,tmp_path)
    with Session(runtime.engine) as db:new=queue(db).id
    class FailingEncoder:
        chunks=encoder.chunks
        def encode(self,*args,**kwargs):raise RuntimeError('synthetic batch failure')
    runtime.encoder=FailingEncoder();assert runtime.run_once()
    with Session(runtime.engine) as db:
        assert db.get(IndexState,1).active_id==old
        failed=db.get(IndexGeneration,new);assert failed.state=='failed'
        failed.state='queued';db.commit()
    runtime.encoder=encoder
    claimed=runtime.claim()
    with Session(runtime.engine) as db:
        job=db.get(IndexGeneration,new);job.lease_until=now()-timedelta(seconds=1);db.commit()
    assert runtime.run_once()
    with Session(runtime.engine) as db:
        job=db.get(IndexGeneration,new);assert job.state=='ready' and job.attempts==3
        assert db.get(IndexState,1).active_id==new
    assert not runtime.build(claimed)  # Old owner cannot publish.


def test_search_api_permission_inspection_and_validation(docs,encoder,tmp_path):
    runtime,v,jid=indexed(docs,encoder,tmp_path)
    client,_,engine,headers=docs
    assert client.get('/search/status').status_code==401
    assert client.post('/search',headers=headers,json={'question':'x','count':99}).status_code==422
    assert client.post('/search',headers=headers,json={'question':'farmers','published_after':'2026-01-01','published_before':'2025-01-01'}).status_code==422
    with Session(engine) as db:user=db.scalar(select(User));user.role='user';db.commit()
    assert client.get('/search/status',headers=headers).status_code==200
    assert client.get(f"/search/versions/{v['id']}/pages/1",headers=headers).status_code==200
    assert client.get(f"/admin/documents/versions/{v['id']}/original",headers=headers).status_code==403
    assert client.post('/admin/index/rebuild',headers=headers).status_code==403
    assert client.post(f"/admin/documents/versions/{v['id']}/reviews",headers=headers,json={}).status_code==403


def test_internal_service_auth_and_real_query(docs,encoder,tmp_path):
    runtime,v,jid=indexed(docs,encoder,tmp_path)
    from backend.index import service
    with TestClient(service(runtime,'synthetic-internal-test-key'),base_url='http://127.0.0.1:8011') as client:
        assert client.post('/query',json={'question':'farmers annual financial support'}).status_code==403
        import time
        for _ in range(40):
            response=client.post('/query',headers={'X-Index-Key':'synthetic-internal-test-key'},json={'question':'How much money do farmers receive every year?'})
            if response.status_code!=503 or response.json()['detail']!='Index busy': break
            time.sleep(0.05)  # Real startup worker owns the runtime briefly; callers receive a retryable busy state.
        assert response.status_code==200 and response.json()['status']=='results'
        assert encoder.tokens('qz '*600,query=True)>512
        assert client.post('/query',headers={'X-Index-Key':'synthetic-internal-test-key'},json={'question':'qz '*600}).status_code==422


def test_real_claim_process_interruption_and_single_owner_lock(docs,encoder,tmp_path):
    runtime,v,old=indexed(docs,encoder,tmp_path)
    with Session(runtime.engine) as db:
        queued=queue(db).id
        assert queue(db).id==queued  # Duplicate rebuild requests share a pending generation.
    code="""import sys,time
sys.path.insert(0,'backend')
from app.config import Settings
from app.database import make_engine
from app.vector_index import Runtime
r=Runtime.__new__(Runtime);r.engine=make_engine(Settings(),test=True)
c=r.claim();print(str(c[0]),flush=True)
time.sleep(60)
"""
    child=subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
    try:
        assert child.stdout.readline().strip()==str(queued)
        child.terminate();child.wait(timeout=10)
        with Session(runtime.engine) as db:
            job=db.get(IndexGeneration,queued)
            assert job.state=='processing' and job.attempts==1
            job.lease_until=now()-timedelta(seconds=1);db.commit()
        assert runtime.run_once()
        with Session(runtime.engine) as db:
            assert db.get(IndexGeneration,queued).state=='ready'
            assert db.get(IndexGeneration,queued).attempts==2
    finally:
        if child.poll() is None:child.kill();child.wait()
    from filelock import FileLock
    lock=str(tmp_path/'test-vectors'/'owner.lock')
    with FileLock(lock,timeout=0):
        attempt=subprocess.run([sys.executable,'-c',
            'from filelock import FileLock,Timeout; import sys\ntry:\n with FileLock(sys.argv[1],timeout=0): print("owned")\nexcept Timeout: print("blocked")',lock],
            capture_output=True,text=True,timeout=10)
        assert attempt.returncode==0 and attempt.stdout.strip()=='blocked'
