"""Real OCR/E5/PostgreSQL with isolated generated test scans and private pack copies."""
from datetime import timedelta
from pathlib import Path
import shutil
import time
from uuid import UUID
import pymupdf
import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from app.config import Settings
from app.auth import now
from app.language import normalize
from app.ocr import queue,run_once,prepared,run_page,claim,owned
from app.ocr_models import ExtractionRevision,ExtractionPage
from app.document_models import ExtractedPage,DocumentVersion
from app.models import User
from app.answer_models import AnswerWorker
from app.extraction_artifacts import pages_for,page_for
from app.eligibility import eligibility
from app.citations import context_for,access_status
from app.grounding import Evidence
from app.grounding import raw_prompt,quote_options,expand_model_output
from app.answer_worker import Worker
from test_answers_postgres import HostDouble,NoGeneration
import asyncio
from app.vector_index import Runtime,queue as queue_index
from app.ingestion import run_once as ingest
from test_auth_postgres import postgres
from test_documents_postgres import docs,upload,pdf
from test_retrieval_postgres import encoder
from ocr_fixtures import scan,REFERENCES,error_rate


def prepare_fixture(docs):
    client,settings,engine,headers=docs
    source,_=prepared(Settings())
    packs=settings.data_dir.parent/'ocr';packs.mkdir(exist_ok=True)
    for name in ('eng.traineddata','hin.traineddata','prepared.json'):shutil.copyfile(source/name,packs/name)
    document=pymupdf.open(stream=pdf(),filetype='pdf')
    for key in ('english','hindi'):
        scanned=pymupdf.open(stream=scan(REFERENCES[key]),filetype='pdf');document.insert_pdf(scanned);scanned.close()
    data=document.tobytes();document.close()
    v=upload(docs,data).json()['version'];assert ingest(engine,settings)
    with Session(engine) as db:
        originals={p.id:p.text for p in db.scalars(select(ExtractedPage))}
    response=client.post(f"/admin/ocr/versions/{v['id']}/queue",headers=headers)
    assert response.status_code==200
    rid=response.json()['id']
    assert client.post(f"/admin/ocr/versions/{v['id']}/queue",headers=headers).json()['id']==rid
    assert run_once(engine,settings)
    return v,rid,originals


def accept_pages(docs,rid):
    client,_,_,headers=docs
    for page in client.get('/admin/ocr/'+rid,headers=headers).json()['pages']:
        if page['method']=='ocr':
            response=client.post(f"/admin/ocr/pages/{page['id']}/reviews",headers=headers,
                json={'decision':'accepted','reason':'Synthetic transcript compared exactly; amounts, dates, categories and negation checked.',
                    'checked_values_dates_categories_negation':True})
            assert response.status_code==200


def test_real_ocr_digital_preservation_review_and_revision_citations(docs,encoder,tmp_path):
    client,settings,engine,headers=docs
    v,rid,originals=prepare_fixture(docs)
    with Session(engine) as db:
        assert {p.id:p.text for p in db.scalars(select(ExtractedPage))}==originals
        pairs=pages_for(db,UUID(v['id']),rid)
        assert [p.pdf_page_number for p,_ in pairs]==[1,2,3]
        assert pairs[0][1].text==pairs[0][0].text and pairs[0][1].method=='digital'
        for key,(_,p) in zip(('english','hindi'),pairs[1:]):
            assert error_rate(REFERENCES[key],p.text)==0 and p.boxes and p.signals['mean_word_confidence']>0
            assert not eligibility(db,db.get(DocumentVersion,UUID(v['id'])))['eligible']
    # Unreviewed OCR cannot enter retrieval or any new assessment.
    pending_runtime=Runtime(settings,engine,encoder=encoder,vector_dir=tmp_path/'pending-ocr-vectors')
    with Session(engine) as db:queue_index(db)
    assert pending_runtime.run_once()
    assert pending_runtime.search('Historical fictional policy annual assistance in 2025?')['items']==[]
    class PendingRetriever:
        async def retrieve(self,question,filters):return pending_runtime.search(question)
    worker=Worker(settings,engine,HostDouble(),generator=NoGeneration(),retriever=PendingRetriever());worker.recover()
    run_id=client.post('/ask',headers=headers,json={'question':'Historical fictional policy annual assistance in 2025?'}).json()['id']
    assert asyncio.run(worker.once())
    audit=client.get('/ask/history/'+run_id,headers=headers).json()['evidence_quality']
    assert audit['status']=='needs_clarification' and audit['source_references']==[]
    assert audit['available_weight_coverage']==0 and audit['components']['citation_coverage']['value'] is None
    accept_pages(docs,rid)
    assert client.get('/admin/ocr/'+rid,headers=headers).json()['state']=='completed'
    # OCR review cannot supply missing rights/provenance approval.
    with Session(engine) as db:assert not eligibility(db,db.get(DocumentVersion,UUID(v['id'])))['eligible']
    assert client.post(f"/admin/documents/versions/{v['id']}/reviews",headers=headers,json={
        'decision':'verified','reuse_status':'permission_recorded','applicability':'historical',
        'reason':'Self-authored synthetic fixture rights only, isolated test database.',
        'evidence_url':'https://example.gov.in/test','scope':'Test-only synthetic transcription; never official government evidence.'}).status_code==200
    runtime=Runtime(settings,engine,encoder=encoder,vector_dir=tmp_path/'ocr-vectors')
    with Session(engine) as db:queue_index(db)
    assert runtime.run_once()
    response=runtime.search('Fictional policy annual assistance of Rs 6,000 in three instalments?')
    passage=next(p for p in response['items'] if p['pdf_page_number']==2)
    assert passage['extraction_revision_id']==rid and passage['extraction_method']=='ocr'
    with Session(engine) as db:
        citation=context_for(db,Evidence(id=passage['chunk_id'],quote=passage['text'],
            quote_start_offset=passage['start_offset'],quote_end_offset=passage['end_offset']),passage)
    newer=client.post(f"/admin/ocr/versions/{v['id']}/queue",headers=headers).json()['id']
    assert newer!=rid;assert run_once(engine,settings);accept_pages(docs,newer)
    with Session(engine) as db:
        assert access_status(db,citation['metadata'])['allowed']
        queue_index(db)
    assert runtime.run_once()
    with Session(engine) as db:assert access_status(db,citation['metadata'])['allowed']
    client.app.state.settings=settings.model_copy(update={'ocr_max_pixels':1_000_000})
    failed=client.post(f"/admin/ocr/versions/{v['id']}/queue",headers=headers).json()['id']
    assert run_once(engine,settings)
    assert client.get('/admin/ocr/'+failed,headers=headers).json()['state']=='partial'
    with Session(engine) as db:assert access_status(db,citation['metadata'])['allowed']
    assert runtime.search('Fictional policy annual assistance of Rs 6,000 in three instalments?')['status']=='results'
    assert client.patch(f"/admin/documents/{v['document_id']}/archive",headers=headers,json={'archived':True}).status_code==200
    with Session(engine) as db:assert not access_status(db,citation['metadata'])['allowed']


def test_ocr_permissions_immutable_reviews_and_restart_fencing(docs):
    client,settings,engine,headers=docs
    v,rid,_=prepare_fixture(docs)
    page=next(p for p in client.get('/admin/ocr/'+rid,headers=headers).json()['pages'] if p['method']=='ocr')
    with Session(engine) as db:
        row=db.get(ExtractionPage,UUID(page['id']));row.text='forbidden overwrite'
        with pytest.raises(DBAPIError):db.commit()
        db.rollback();user=db.scalar(select(User));user.role='user';db.commit()
    for path in (f"/admin/ocr/versions/{v['id']}",f"/admin/ocr/pages/{page['id']}/text"):
        assert client.get(path,headers=headers).status_code==403
    assert client.post(f"/admin/ocr/versions/{v['id']}/queue",headers=headers).status_code==403
    assert client.post(f"/admin/ocr/pages/{page['id']}/reviews",headers=headers,json={
        'decision':'accepted','reason':'This unauthorized review must never be saved.',
        'checked_values_dates_categories_negation':True}).status_code==403
    with Session(engine) as db:
        user=db.scalar(select(User));user.role='admin'
        r=db.get(ExtractionRevision,UUID(rid));r.state='queued';r.attempts=0;db.commit()
    first=claim(engine)
    with Session(engine) as db:
        r=db.get(ExtractionRevision,UUID(rid));r.lease_until=now()-timedelta(seconds=1);db.commit()
    second=claim(engine);assert first[1]!=second[1]
    with Session(engine) as db:assert owned(db,*first) is None
    # Same successful page artifacts are reused on recovery; a stale owner cannot publish.
    with Session(engine) as db:
        r=db.get(ExtractionRevision,UUID(rid));r.lease_until=now()-timedelta(seconds=1);db.commit()
    assert run_once(engine,settings)
    with Session(engine) as db:
        assert len(list(db.scalars(select(ExtractionPage))))==3
        assert db.get(ExtractionRevision,UUID(rid)).attempts==3


def test_real_ocr_timeout_pixels_low_quality_and_cleanup(docs,tmp_path):
    _,settings,_,_=docs
    packs,manifest=prepared(Settings())
    path=tmp_path/'scan.pdf';path.write_bytes(scan(REFERENCES['english']))
    request={'path':str(path),'ordinal':1,'manifest':manifest,'packs':str(packs),
        'dpi':300,'max_pixels':12000000,'seconds':0.01}
    started=time.monotonic();assert run_page(settings,request,lambda:True)['error']=='ocr_timeout'
    assert time.monotonic()-started<10
    assert not list((settings.data_dir/'temporary').glob('ocr-*'))
    request.update(seconds=30,max_pixels=100)
    assert run_page(settings,request,lambda:True)['error']=='ocr_pixel_limit'
    path.write_bytes(pdf(pages=('',)))
    request.update(max_pixels=12000000)
    result=run_page(settings,request,lambda:True)
    assert 'low_quality' in result['quality_flags'] and not result['text']
    assert not list((settings.data_dir/'temporary').glob('ocr-*'))


def test_safe_language_normalization_and_uncertain_scheme():
    question='  २०२५ PM Kisan: saalana ६,००० रुपये, ३ kiste? bina OTP, nahi fingerprint; Ravi 01/08/2025  '
    result=normalize(question)
    assert result['original_question']==question
    for value in ('2025','6,000','3','without OTP','not fingerprint','Ravi','01/08/2025','annual'):
        assert value in result['retrieval_question']
    assert normalize('PM-KISAN')['detected_language']=='uncertain'
    assert 'today' in normalize('aaj PM Kisan me patra hun?')['retrieval_question']


def test_response_profile_and_explicit_language(docs):
    client,_,engine,headers=docs
    with Session(engine) as db:
        user=db.scalar(select(User));user.preferred_language='hinglish'
        db.add(AnswerWorker(id=1,heartbeat=now()));db.commit()
    question='  २०२५ PM Kisan saalana kitna paisa?  '
    response=client.post('/ask',headers=headers,json={'question':question})
    assert response.status_code==202 and response.json()['language']=='hi'
    assert response.json()['question']==question and '2025' in response.json()['retrieval_question']
    assert client.post('/ask/history/'+response.json()['id']+'/cancel',headers=headers).status_code==200
    response=client.post('/ask',headers=headers,json={'question':question,'language':'en'})
    assert response.status_code==202 and response.json()['language']=='en'


def test_partial_failure_retry_bounds_and_low_quality_exclusion(docs):
    client,settings,engine,headers=docs
    source,_=prepared(Settings());packs=settings.data_dir.parent/'ocr';packs.mkdir(exist_ok=True)
    for name in ('eng.traineddata','hin.traineddata','prepared.json'):shutil.copyfile(source/name,packs/name)
    v=upload(docs,pdf(pages=('',))).json()['version'];assert ingest(engine,settings)
    rid=client.post(f"/admin/ocr/versions/{v['id']}/queue",headers=headers).json()['id']
    for attempt in range(1,4):
        assert run_once(engine,settings)
        detail=client.get('/admin/ocr/'+rid,headers=headers).json()
        assert detail['state']=='partial' and detail['attempts']==attempt
        page=detail['pages'][0]
        assert 'low_quality' in page['quality_flags']
        assert client.post('/admin/ocr/pages/'+page['id']+'/reviews',headers=headers,json={
            'decision':'accepted','reason':'Blank low-quality fixture must not become accepted transcription.',
            'checked_values_dates_categories_negation':True}).status_code==409
        with Session(engine) as db:assert not eligibility(db,db.get(DocumentVersion,UUID(v['id'])))['eligible']
        response=client.post('/admin/ocr/'+rid+'/retry',headers=headers)
        assert response.status_code==(200 if attempt<3 else 409)
    with Session(engine) as db:
        assert len(list(db.scalars(select(ExtractionPage))))==3
        assert all(p.text=='' for p in db.scalars(select(ExtractionPage)))


def test_complete_annual_excerpt_handles_preserve_conditions():
    import json
    text='Cumulative disbursement of Rs 22,000 crore in 2025.\n\nLand-holding farmer families receive financial benefit of Rs 6,000 per year in three instalments; conditions apply.'
    passage={'chunk_id':'test-only','text':text,'start_offset':100,'title':'Synthetic fixture','publication_date':'2025-08-01',
        'verification':{'scope':'Test only','applicability':'historical'}}
    prompt=raw_prompt('According to the 2025 factsheet, annual financial assistance?','hi',[passage])
    data=json.loads(prompt.split('<|im_start|>user\n')[1].split('<|im_end|>')[0])
    assert list(data['sources'][0]['excerpts'])==['Q2']
    assert data['sources'][0]['excerpts']['Q2']==quote_options(passage)['Q2']
    output=expand_model_output(json.dumps({'status':'answered','language':'hi','limitations':[],
        'claims':[{'text':'भूमिधारक किसान परिवारों को प्रति वर्ष 6,000 रुपये की सहायता 3 किस्तों में मिलती है।',
            'evidence':[{'id':'test-only','quote_id':'Q2'}]}]},ensure_ascii=False),'hi',[passage])
    assert output.claims[0].evidence[0].quote_start_offset==100+text.index('Land-holding')


def test_real_descendant_tree_cleanup_on_deadline(docs,tmp_path,monkeypatch):
    # Controlled sleeper tree tests containment; transcription smoke uses actual Tesseract separately.
    import ctypes
    from ctypes import wintypes
    from app import ocr
    _,settings,_,_=docs
    directory=tmp_path/'backend';directory.mkdir(exist_ok=True)
    (directory/'ocr_child.py').write_text('''import sys,subprocess,json,time
from pathlib import Path
sys.stdin.buffer.read(1)
request=json.loads(Path(sys.argv[1]).read_text())
child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])
Path(request['pid_file']).write_text(str(child.pid))
time.sleep(60)
''',encoding='utf-8')
    monkeypatch.setattr(ocr,'ROOT',tmp_path)
    pid_file=tmp_path/'child-pid.txt'
    result=run_page(settings,{'seconds':1,'pid_file':str(pid_file)},lambda:True)
    assert result['error']=='ocr_timeout' and pid_file.exists()
    pid=int(pid_file.read_text())
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x100000,False,pid)
    if handle:
        try:assert kernel.WaitForSingleObject(handle,5000)==0
        finally:kernel.CloseHandle(handle)
    assert not list((settings.data_dir/'temporary').glob('ocr-*'))


def test_hindi_annual_construction_keeps_digital_source_scope():
    from app.language import hindi_annual
    from app.grounding import GroundedOutput,Claim
    text='PM-KISAN scheme aims to supplement the financial needs of land-holding farmers. Under the scheme, a financial benefit of Rs 6,000/- per year is transferred in three equal instalments.'
    evidence=Evidence(id='test-only',quote=text)
    output=GroundedOutput(status='answered',language='hi',claims=[Claim(text='दस्तावेज़ में वार्षिक सहायता का विवरण है।',evidence=[evidence])],limitations=[])
    passage={'chunk_id':'test-only','text':text,'publication_date':'2025-08-01','extraction_method':'digital'}
    final,rule=hindi_annual(output,'2025 annual benefit for farmer families?',[passage])
    assert rule=='annual-hi-digital-fields-v1' and final.status=='partial'
    assert 'insufficient_scope' in final.limitations
    assert 'भूमिधारक किसानों' in final.claims[0].text and '6,000' in final.claims[0].text and '3 बराबर किस्तों' in final.claims[0].text
    assert 'परिवार' not in final.claims[0].text and final.claims[0].evidence==[evidence]
    assert hindi_annual(output,'annual benefit?',[{**passage,'extraction_method':'ocr'}])==(output,None)
    assert hindi_annual(output,'annual benefit?',[{**passage,'text':'Unrelated excerpt'}])==(output,None)


def test_filtered_generation_cannot_choose_unsupplied_quote():
    import json
    from app.grounding import RagError
    passage={'chunk_id':'test-only','text':'Cumulative disbursement of Rs 22,000 crore.\n\nFinancial benefit of Rs 6,000 per year; conditions apply.','start_offset':0}
    raw=json.dumps({'status':'answered','language':'hi','limitations':[], 'claims':[{'text':'दस्तावेज़ का विवरण।','evidence':[{'id':'test-only','quote_id':'Q1'}]}]})
    with pytest.raises(RagError,match='invented_quote_id'):
        expand_model_output(raw,'hi',[passage],'annual benefit?')


def test_hindi_chatbot_requires_exact_positive_digital_names():
    from app.language import hindi_chatbot
    from app.grounding import GroundedOutput,Claim
    text='PM-KISAN AI CHATBOT. It has been developed and improved with the support of EKstep foundation and Bhashini.'
    output=GroundedOutput(status='partial',language='hi',claims=[Claim(text='सहयोग का विवरण।',evidence=[Evidence(id='test-only',quote=text)])],limitations=[])
    passage={'chunk_id':'test-only','text':text,'publication_date':'2025-08-01','extraction_method':'digital'}
    final,rule=hindi_chatbot(output,'2025 chatbot organisations?',[passage])
    assert rule=='chatbot-hi-digital-names-v1' and final.status=='partial'
    assert 'EKstep foundation और Bhashini' in final.claims[0].text
    assert final.claims[0].evidence==output.claims[0].evidence
    assert hindi_chatbot(output,'chatbot organisations?',[{**passage,'extraction_method':'ocr'}])==(output,None)
    assert hindi_chatbot(output,'chatbot launch date?',[passage])==(output,None)
    assert hindi_chatbot(output,'chatbot organisations?',[{**passage,'text':'Unrelated'}])==(output,None)
