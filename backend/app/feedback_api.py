"""Current private feedback is data, never model input or evidence-quality scoring."""
from uuid import UUID
from typing import Literal
import unicodedata
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from .answer_models import AnswerFeedback
from .ask_api import owned, view
from .auth import current_user, csrf, now
from .database import get_db
from .models import User

router=APIRouter(tags=['private feedback'])

class FeedbackInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    vote: Literal['helpful','not_helpful']
    reason: Literal['unclear_wording','incomplete_answer','citation_issue','language_issue','suspected_factual_error'] | None=None
    comment: str | None=Field(default=None,max_length=500)

    @field_validator('comment')
    @classmethod
    def plain_text(cls,value):
        if value is None:return None
        if any(unicodedata.category(c) in ('Cc','Cs') and c not in '\n\t' for c in value):
            raise ValueError('Comment contains unsupported control characters')
        return value.strip() or None

def accessible(db,user,run_id):
    run=owned(db,user,run_id,lock=True)
    if not view(db,run)['can_feedback']:
        raise HTTPException(409,'Feedback requires an accessible answered or partial result within 30 days')
    return run

@router.get('/ask/history/{run_id}/feedback')
def get_feedback(run_id:UUID,user:User=Depends(current_user),db:Session=Depends(get_db)):
    run=accessible(db,user,run_id)
    return {'feedback':view(db,run)['feedback']}

@router.put('/ask/history/{run_id}/feedback',dependencies=[Depends(csrf)])
def put_feedback(run_id:UUID,body:FeedbackInput,user:User=Depends(current_user),db:Session=Depends(get_db)):
    run=accessible(db,user,run_id)
    stmt=insert(AnswerFeedback).values(user_id=user.id,run_id=run.id,**body.model_dump())
    db.execute(stmt.on_conflict_do_update(index_elements=['user_id','run_id'],
        set_={**body.model_dump(),'updated_at':now()},
        where=or_(AnswerFeedback.vote.is_distinct_from(stmt.excluded.vote),
                  AnswerFeedback.reason.is_distinct_from(stmt.excluded.reason),
                  AnswerFeedback.comment.is_distinct_from(stmt.excluded.comment))))
    db.expire_all()
    result=view(db,run)['feedback']  # Response captured while the serialized parent lock is still held.
    db.commit()
    return {'feedback':result}

@router.delete('/ask/history/{run_id}/feedback',dependencies=[Depends(csrf)])
def remove_feedback(run_id:UUID,user:User=Depends(current_user),db:Session=Depends(get_db)):
    run=accessible(db,user,run_id)
    db.execute(delete(AnswerFeedback).where(AnswerFeedback.user_id==user.id,AnswerFeedback.run_id==run.id))
    db.commit()
    return {'feedback':None}
