"""Owned asynchronous Ask jobs; one global pending request, no hidden inference queue."""
from datetime import timedelta
from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import Field
from sqlalchemy import select,text
from sqlalchemy.orm import Session
from .auth import current_user,csrf,now,throttle
from .database import get_db
from .models import User
from .answer_models import AnswerRun, AnswerWorker
from .search_api import SearchInput
from .eligibility import eligibility
from .document_models import DocumentVersion
from .citations import citation_views,access_status
from .index_models import IndexPassage
from .document_models import ExtractedPage
from .documents import page_text
from copy import deepcopy
from .support import METHOD

router=APIRouter(tags=['answers'])


class AskInput(SearchInput):
    language: Literal['en','hi']='en'
    count: Literal[5]=5  # The preserved retrieval baseline uses five candidates.


def owned(db,user,run_id):
    run=db.scalar(select(AnswerRun).where(AnswerRun.id==run_id,AnswerRun.user_id==user.id))
    if not run: raise HTTPException(404,'Answer record not found')
    return run


def view(db,run,detail=True):
    result={'id':str(run.id),'question':run.question,'language':run.language,'state':run.state,
        'status':run.result['status'] if run.result else None,'created_at':run.created_at,'error_code':run.error_code}
    if detail:
        warnings=[]
        withheld=False
        for p in sorted(run.sources,key=lambda p:p['version_id']):
            access=access_status(db,{'version_id':p['version_id'],'passage_id':p['chunk_id'],'review':p['verification']})
            if not access['allowed']:
                withheld=True
                warnings.append({'version_id':p['version_id'],'reasons':access['reasons'],
                    'warning':'Historical snapshot preserved privately; answer/excerpts withheld because current source access or provenance changed.'})
        answer=deepcopy(run.result)
        sources=deepcopy(run.sources)
        citations,checks=citation_views(db,run)
        withheld=withheld or any(not c['current_access']['allowed'] for c in citations)
        if answer:
            if withheld:
                answer['answer']='Historical answer and excerpts withheld under current source-access policy. The private snapshot is unchanged.'
                answer['claims']=[]
            else:
                for position,claim in enumerate(answer['claims'],1):
                    related=[c for c in citations if c['claim_text']==claim['text']]
                    if related:claim.update(claim_id=related[0]['claim_id'],support=related[0]['support'],position=position,
                        citation_markers=[c['marker'] for c in related])
        if withheld:
            for s in sources:s['text']=None
            for c in citations:c['quote']=None;c['claim_text']=None
        result.update(result=answer,sources=sources,citations=citations,claim_checks=checks,source_access_withheld=withheld,current_support_method=METHOD,
            model=run.model,timings=run.timings,
            finished_at=run.finished_at,current_source_warnings=warnings,
            retention='Private records expire after 30 days; no raw prompts or thinking stored.')
    return result


@router.get('/ask/history/{run_id}/citations/{citation_id}/text')
def citation_text(run_id:UUID,citation_id:UUID,user:User=Depends(current_user),db:Session=Depends(get_db)):
    run=owned(db,user,run_id)
    citations,_=citation_views(db,run)
    citation=next((c for c in citations if c['citation_id']==str(citation_id)),None)
    if not citation:raise HTTPException(404,'Citation not found')
    if not citation['current_access']['allowed']:raise HTTPException(403,'Current source-access policy withholds this excerpt')
    m=citation['metadata'];passage=db.get(IndexPassage,UUID(m['passage_id']))
    page=db.get(ExtractedPage,passage.page_id) if passage else None
    start,end=citation['start_offset'],citation['end_offset']
    if not page or str(page.version_id)!=m['version_id'] or not (passage.start_offset<=start<end<=passage.end_offset) or page.text[start:end]!=citation['quote']:
        raise HTTPException(503,'Referenced original provenance is unavailable or changed')
    window=page_text(UUID(m['version_id']),page.ordinal,max(0,start-300),db)
    return {'citation_id':str(citation_id),'quote_start_offset':start,'quote_end_offset':end,**window}


@router.get('/ask/status')
def worker_status(user:User=Depends(current_user),db:Session=Depends(get_db)):
    worker=db.get(AnswerWorker,1)
    return {'worker_available':bool(worker and worker.heartbeat>now()-timedelta(seconds=15)),
            'trust_score':None,'pending_limit':1}


@router.post('/ask',status_code=202,dependencies=[Depends(csrf)])
def ask(body:AskInput,request:Request,user:User=Depends(current_user),db:Session=Depends(get_db)):
    throttle(db,request,str(user.id),'ask')
    db.execute(text('SELECT pg_advisory_xact_lock(28051)'))
    worker=db.get(AnswerWorker,1)
    if not worker or worker.heartbeat<now()-timedelta(seconds=15): raise HTTPException(503,'Answer worker unavailable; start the prepared local RAG service')
    if db.scalar(select(AnswerRun.id).where(AnswerRun.state.in_(['queued','processing'])).limit(1)):
        raise HTTPException(503,'Answer service busy; one pending request is allowed')
    filters=body.model_dump(mode='json',exclude={'question','language','count'})
    run=AnswerRun(user_id=user.id,question=body.question,language=body.language,filters=filters)
    db.add(run);db.commit()
    return view(db,run)


@router.get('/ask/history')
def history(page:int=Query(default=1,ge=1),user:User=Depends(current_user),db:Session=Depends(get_db)):
    runs=db.scalars(select(AnswerRun).where(AnswerRun.user_id==user.id).order_by(AnswerRun.created_at.desc()).offset((page-1)*20).limit(20))
    return {'items':[view(db,r,False) for r in runs]}


@router.get('/ask/history/{run_id}')
def detail(run_id:UUID,user:User=Depends(current_user),db:Session=Depends(get_db)):
    return view(db,owned(db,user,run_id))


@router.post('/ask/history/{run_id}/cancel',dependencies=[Depends(csrf)])
def cancel(run_id:UUID,user:User=Depends(current_user),db:Session=Depends(get_db)):
    run=owned(db,user,run_id)
    db.refresh(run,with_for_update=True)
    if run.state=='queued': run.state='cancelled';run.finished_at=now()
    elif run.state=='processing': run.cancel_requested=True
    db.commit();return view(db,run)
