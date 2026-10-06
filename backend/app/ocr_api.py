"""Admin-only OCR queue, immutable text inspection and append-only manual decisions."""
from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .auth import admin_user, csrf
from .database import get_db
from .document_models import DocumentVersion, Document, ExtractedPage
from .models import User
from .ocr_models import ExtractionRevision, ExtractionPage, ExtractionReview
from .extraction_artifacts import pages_for, review_for
from . import ocr

router = APIRouter(prefix='/admin/ocr',tags=['OCR'],dependencies=[Depends(admin_user)])


def job(db, revision_id):
    revision = db.get(ExtractionRevision,revision_id,with_for_update=True)
    if not revision:raise HTTPException(404,'Extraction revision not found')
    return revision


def view(db, revision):
    return {'id':str(revision.id),'version_id':str(revision.version_id),'state':revision.state,'attempts':revision.attempts,
        'processed':revision.processed,'total':revision.total,'error_code':revision.error_code,'spec':revision.spec,
        'pages':[{'id':str(p.id),'ordinal':original.ordinal,'pdf_page_number':original.pdf_page_number,
            'attempt':p.attempt,'method':p.method,'characters':len(p.text),'quality_flags':p.quality_flags,
            'signals':p.signals,'review':review_for(db,p).decision if review_for(db,p) else None}
            for original,p in pages_for(db,revision.version_id,revision.id)]}


@router.post('/versions/{version_id}/queue',dependencies=[Depends(csrf)])
def queue(version_id:UUID,request:Request,user:User=Depends(admin_user),db:Session=Depends(get_db)):
    try:return view(db,ocr.queue(db,request.app.state.settings,version_id,user.id))
    except (ValueError,OSError,KeyError):raise HTTPException(409,'OCR requires prepared English/Hindi packs, a non-archived PDF and completed initial extraction with flagged pages') from None


@router.get('/versions/{version_id}')
def revisions(version_id:UUID,db:Session=Depends(get_db)):
    return {'items':[view(db,r) for r in db.scalars(select(ExtractionRevision).where(ExtractionRevision.version_id==version_id)
        .order_by(ExtractionRevision.created_at.desc()).limit(20))]}


@router.get('/{revision_id}')
def detail(revision_id:UUID,db:Session=Depends(get_db)):return view(db,job(db,revision_id))


@router.post('/{revision_id}/retry',dependencies=[Depends(csrf)])
def retry(revision_id:UUID,db:Session=Depends(get_db)):
    revision=job(db,revision_id)
    version=db.get(DocumentVersion,revision.version_id,with_for_update=True)
    if revision.state not in ('failed','partial') or revision.attempts>=3 or db.get(Document,version.document_id).archived_at:
        raise HTTPException(409,'Only non-archived failed/partial OCR below three attempts can retry')
    pending=db.scalar(select(ExtractionRevision.id).where(ExtractionRevision.version_id==revision.version_id,
        ExtractionRevision.id!=revision.id,ExtractionRevision.state.in_(['queued','processing','pending_review'])))
    if pending:raise HTTPException(409,'Another revision is pending')
    revision.state,revision.error_code='queued',None;db.commit();return view(db,revision)


@router.post('/{revision_id}/cancel',dependencies=[Depends(csrf)])
def cancel(revision_id:UUID,db:Session=Depends(get_db)):
    revision=job(db,revision_id)
    if revision.state not in ('queued','processing'):raise HTTPException(409,'Only a pending job can cancel')
    revision.state='cancelled';revision.lease_owner=revision.lease_until=None;db.commit();return view(db,revision)


@router.get('/pages/{page_id}/text')
def page_text(page_id:UUID,offset:int=0,db:Session=Depends(get_db)):
    page=db.get(ExtractionPage,page_id)
    if not page:raise HTTPException(404,'Extraction page not found')
    if offset<0 or offset>len(page.text):raise HTTPException(422,'Invalid text offset')
    return {'id':str(page.id),'text':page.text[offset:offset+20000],'offset':offset,'total_characters':len(page.text),
        'quality_flags':page.quality_flags,'signals':page.signals,'boxes':page.boxes,'method':page.method,
        'revision_id':str(page.revision_id),'raw_ocr_preserved':page.method=='ocr'}


class Review(BaseModel):
    model_config=ConfigDict(extra='forbid')
    decision:Literal['accepted','rejected']
    reason:str=Field(min_length=20,max_length=2000)
    checked_values_dates_categories_negation:Literal[True]


@router.post('/pages/{page_id}/reviews',dependencies=[Depends(csrf)])
def review(page_id:UUID,body:Review,user:User=Depends(admin_user),db:Session=Depends(get_db)):
    page=db.get(ExtractionPage,page_id)
    if not page:raise HTTPException(404,'Extraction page not found')
    revision=job(db,page.revision_id)
    version=db.get(DocumentVersion,revision.version_id,with_for_update=True)
    if revision.state in ('queued','processing','cancelled','failed') or db.get(Document,version.document_id).archived_at:
        raise HTTPException(409,'Review requires finished non-archived extraction')
    latest=dict((p.page_id,p.id) for _,p in pages_for(db,revision.version_id,revision.id))
    if latest.get(page.page_id)!=page.id:raise HTTPException(409,'This attempt is superseded within the revision')
    if page.method!='ocr' or ('low_quality' in page.quality_flags and body.decision=='accepted'):
        raise HTTPException(409,'Only legible OCR can be accepted; low quality requires a new extraction attempt')
    db.add(ExtractionReview(page_id=page.id,reviewer_id=user.id,decision=body.decision,reason=body.reason))
    db.flush();ocr.refresh_state(db,revision);db.commit()
    return view(db,revision)
