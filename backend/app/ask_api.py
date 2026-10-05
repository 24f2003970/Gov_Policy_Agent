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
        for p in run.sources:
            v=db.get(DocumentVersion,UUID(p['version_id']))
            e=eligibility(db,v) if v else None
            if not e or not e['eligible'] or e['review_id']!=p['verification']['review_id']:
                warnings.append({'version_id':p['version_id'],'warning':'Historical answer snapshot; source eligibility/review has changed.'})
        result.update(result=run.result,sources=run.sources,model=run.model,timings=run.timings,
            finished_at=run.finished_at,current_source_warnings=warnings,
            retention='Private records expire after 30 days; no raw prompts or thinking stored.')
    return result


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
