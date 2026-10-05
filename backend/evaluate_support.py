"""Read-only original-source dev checks. Stop rag.py; keep the index owner running."""
import asyncio
from copy import deepcopy
import json
import statistics
import time
from filelock import FileLock
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config import ROOT,Settings
from app.database import make_engine
from app.document_models import DocumentVersion,ExtractedPage
from app.index_models import IndexPassage,IndexState
from app.eligibility import eligibility
from app.citations import context_for
from app.grounding import Evidence,Claim,GroundedOutput,RagError
from app.rag_engine import LocalGenerator,LocalRetriever,pipeline
from app.support import SupportVerifier,assessment
from app.ollama_local import OllamaHost


async def evaluate(settings):
    engine=make_engine(settings);generator=LocalGenerator(settings);verifier=SupportVerifier(engine,generator)
    dev=json.loads((ROOT/'docs/support_devset.json').read_text('utf-8'));rows=[]
    for case in dev['cases']:
        began=time.perf_counter();provenance=False
        with Session(engine) as db:
            v=db.scalar(select(DocumentVersion).where(DocumentVersion.checksum==dev['source_sha256']))
            e=eligibility(db,v) if v else None
            if not e or not e['eligible']:raise RuntimeError('Reviewed development source unavailable')
            page=db.scalar(select(ExtractedPage).where(ExtractedPage.version_id==v.id,ExtractedPage.ordinal==case['page']))
            offset=page.text.index(case['anchor'])
            passage=db.scalar(select(IndexPassage).where(IndexPassage.generation_id==db.get(IndexState,1).active_id,
                IndexPassage.page_id==page.id,IndexPassage.start_offset<=offset,IndexPassage.end_offset>offset).order_by(IndexPassage.start_offset))
            if not passage:raise RuntimeError('Development anchor not indexed')
            span=next(s for s in page.paragraphs if s['start']<=offset<s['end'])
            start,end=max(span['start'],passage.start_offset),min(span['end'],passage.end_offset)
            if case.get('mutation')=='short':
                start=page.text.rfind('Rs',passage.start_offset,offset);end=offset+len('6,000')
            quote=page.text[start:end]
            if case.get('mutation')=='fabricate':quote+=' fabricated extra text'
            evidence=Evidence(id=str(passage.id),quote=quote,quote_start_offset=start,quote_end_offset=end)
            try:citation=context_for(db,evidence,{'verification':{'review_id':e['review_id'],'applicability':e['applicability']}});provenance=True
            except RagError as exc:
                if exc.code!='citation_provenance_invalid':raise
                check=assessment('not_evaluated','invalid_provenance')
        if provenance:
            available=None
            if case.get('mutation')=='superseded':citation={**citation,'superseded':True}
            if case.get('mutation')=='conflict':
                other=deepcopy(citation);other['id']='isolated-conflict';other['quote']=other['context']='Financial benefit of Rs 9,000 per year.'
                available=[citation,other]
            try:check=await verifier.check(case['claim'],[citation],available)
            except RagError as exc:check={'outcome':'error','error_code':exc.code,'judge_called':True}
        row={'id':case['id'],'expected':case['expected'],'provenance_valid':provenance,'check':check,
             'wall_ms':round((time.perf_counter()-began)*1000,2)}
        rows.append(row);print(case['id'],check['outcome'],check.get('reason_code') or check.get('error_code'),row['wall_ms'],flush=True)
    negatives=[r for r in rows if r['expected']=='negative'];positives=[r for r in rows if r['expected']=='positive']
    accepted=lambda r:r['check']['outcome']=='supported_by_check'
    timings=[r['wall_ms'] for r in rows if r['check'].get('judge_called')]
    metrics={'negative_count':len(negatives),'false_accept_count':sum(accepted(r) for r in negatives),
        'positive_count':len(positives),'false_reject_count':sum(not accepted(r) for r in positives),
        'provenance_valid_count':sum(r['provenance_valid'] for r in rows),'provenance_attempts':len(rows),
        'accepted_claims':sum(accepted(r) for r in rows),'candidate_claims':len(rows),
        'judge_case_count':len(timings),'judge_case_median_ms':statistics.median(timings) if timings else None,
        'judge_case_min_ms':min(timings) if timings else None,'judge_case_max_ms':max(timings) if timings else None}
    end_to_end=[];retriever=LocalRetriever(settings)
    response=await retriever.retrieve('According to the 2025 PM-KISAN factsheet, annual financial benefit?',{})
    p=next(p for p in response['items'] if '6,000/- per year' in p['text'])
    evidence=Evidence(id=p['chunk_id'],quote=p['text'],quote_start_offset=p['start_offset'],quote_end_offset=p['end_offset'])
    multi=GroundedOutput(status='answered',language='en',claims=[
        Claim(text=dev['cases'][0]['claim'],evidence=[evidence]),
        Claim(text='Land-holding farmers receive Rs 6,000 monthly.',evidence=[evidence])],limitations=[])
    checked,checks,multi_metrics=await verifier.evaluate(multi,response['items'],response['generation'])
    assert checked.status=='partial' and len(checked.claims)==1
    multi_report={'kind':'Isolated two-candidate check against real SQL source; not production one-claim generation',
        'status':checked.status,'retained_claims':len(checked.claims),'candidate_claims':2,'checks':checks,'metrics':multi_metrics}
    for language,question in [('en','According to the 2025 PM-KISAN factsheet, what annual assistance and instalments are described?'),
            ('hi','2025 के पीएम किसान दस्तावेज़ के अनुसार: सालाना कितनी सहायता और कितनी किस्तें दी जाती हैं?'),
            ('en','According to the 2025 PM-KISAN factsheet, how does it aim to protect small and marginal farmers from moneylenders?'),
            ('hi','2025 के पीएम किसान दस्तावेज़ के अनुसार: फेस ऑथेंटिकेशन से बिना ओटीपी ई-केवाईसी कैसे कर सकते थे?')]:
        began=time.perf_counter()
        try:
            result,_,_,timings=await pipeline(question,language,{},retriever,generator,verifier)
            checks=result.pop('_claim_checks',[])
            row={'language':language,'question':question,'result':result,'timings':timings,'checks':checks}
        except RagError as exc:row={'language':language,'question':question,'error':exc.code}
        row['wall_ms']=round((time.perf_counter()-began)*1000,2);end_to_end.append(row)
        print('pipeline',language,row.get('error') or row['result']['status'],row['wall_ms'],flush=True)
    report={'review':dev['review_status'],'model':generator.manifest,'metrics':metrics,'rows':rows,'multiple_claims':multi_report,'end_to_end':end_to_end}
    (ROOT/'runtime/support-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(json.dumps(metrics),flush=True);engine.dispose()


if __name__=='__main__':
    settings=Settings();root=settings.data_dir.parent/'ollama'
    with FileLock(str(root/'owner.lock'),timeout=0),OllamaHost(settings):asyncio.run(evaluate(settings))
