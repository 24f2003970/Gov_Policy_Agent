"""Resolve the exact revision, including historical legacy digital spans."""
from uuid import UUID
from types import SimpleNamespace
from sqlalchemy import select
from .document_models import ExtractedPage
from .ocr_models import ExtractionPage, ExtractionRevision, ExtractionReview, ExtractionState

LATEST = object()


def revision_for(db, version_id):
    state = db.get(ExtractionState, version_id)
    return str(state.ready_id) if state else None


def pages_for(db, version_id, revision_id):
    originals = list(db.scalars(select(ExtractedPage).where(ExtractedPage.version_id == version_id).order_by(ExtractedPage.ordinal)))
    if not revision_id:
        return [(p, p) for p in originals]
    artifacts = list(db.scalars(select(ExtractionPage).where(ExtractionPage.revision_id == UUID(str(revision_id)))
        .order_by(ExtractionPage.attempt)))
    by_page = {p.page_id: p for p in artifacts}
    return [(p, by_page[p.id]) for p in originals if p.id in by_page]


def review_for(db, page):
    return db.scalar(select(ExtractionReview).where(ExtractionReview.page_id == page.id)
        .order_by(ExtractionReview.created_at.desc(), ExtractionReview.id.desc()).limit(1))


def accepted(db, page):
    if page.method == 'digital': return True
    if page.method != 'ocr' or 'low_quality' in page.quality_flags: return False
    review = review_for(db, page)
    return bool(review and review.decision == 'accepted')


def ready(db, version_id, revision_id):
    revision = db.get(ExtractionRevision, UUID(str(revision_id)))
    if not revision or revision.version_id != version_id or revision.state != 'completed': return False
    pages = pages_for(db, version_id, revision_id)
    return len(pages) == revision.total and all(accepted(db, p) for _, p in pages)


def page_for(db, passage):
    original = db.get(ExtractedPage, passage.page_id) if passage else None
    if not original: return None
    if not passage.extraction_page_id: return original
    page = db.get(ExtractionPage, passage.extraction_page_id)
    revision = db.get(ExtractionRevision, page.revision_id) if page else None
    if not page or page.page_id != original.id or not revision or revision.version_id != passage.version_id: return None
    return SimpleNamespace(id=original.id,version_id=original.version_id,ordinal=original.ordinal,
        pdf_page_number=original.pdf_page_number,source_start=original.source_start,
        text=page.text,paragraphs=page.paragraphs,quality_flags=page.quality_flags,method=page.method,
        revision_id=page.revision_id,artifact_id=page.id)


def metadata_for(db, passage):
    page = page_for(db, passage)
    artifact=db.get(ExtractionPage,passage.extraction_page_id) if passage and passage.extraction_page_id else None
    review=review_for(db,artifact) if artifact and artifact.method=='ocr' else None
    return {'extraction_revision_id': str(page.revision_id) if hasattr(page,'artifact_id') else None,
        'extraction_page_id': str(page.artifact_id) if hasattr(page,'artifact_id') else None,
        'extraction_method': page.method if hasattr(page,'artifact_id') else 'digital',
        'extraction_quality_flags': page.quality_flags if page else ['missing'],
        'extraction_review_id': str(review.id) if review else None,
        'extraction_review_status': review.decision if review else 'not_required' if not artifact or artifact.method=='digital' else 'unreviewed',
        'ocr_notice': 'OCR-derived text; manual review and OCR signals do not guarantee transcription or factual accuracy.'
            if hasattr(page,'artifact_id') and page.method == 'ocr' else None}
