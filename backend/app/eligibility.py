from sqlalchemy import select
from .document_models import Document, DocumentVersion, IngestionJob, VersionRelationship
from .index_models import EligibilityReview


def eligibility(db, version):
    document = db.get(Document, version.document_id)
    job = db.scalar(select(IngestionJob).where(IngestionJob.version_id == version.id))
    review = db.scalar(select(EligibilityReview).where(EligibilityReview.version_id == version.id)
        .order_by(EligibilityReview.created_at.desc(), EligibilityReview.id.desc()).limit(1))
    decision = review.decision if review else version.provenance_status
    rights = review.reuse_status if review else version.metadata_snapshot.get('reuse_status')
    reasons = []
    if review is None: reasons.append('audit_review_required')
    if document.archived_at: reasons.append('archived')
    if not job or job.state != 'completed': reasons.append('extraction_' + (job.state if job else 'missing'))
    if decision != 'verified': reasons.append('provenance_' + decision)
    if rights != 'permission_recorded': reasons.append('reuse_' + str(rights))
    if db.scalar(select(VersionRelationship.id).where(VersionRelationship.to_version_id == version.id,
            VersionRelationship.kind == 'supersedes').limit(1)):
        reasons.append('explicitly_superseded')
    return {'eligible': not reasons, 'reasons': reasons, 'provenance': decision, 'reuse_status': rights,
        'applicability': review.applicability if review else 'unknown',
        'review_id': str(review.id) if review else None,
        'scope': review.scope if review else 'No audited intended-use scope recorded',
        'evidence_url': review.evidence_url if review else None}


def source_snapshot(db):
    versions = list(db.scalars(select(DocumentVersion).order_by(DocumentVersion.ingested_at, DocumentVersion.id)))
    if len(versions) > 100:
        raise ValueError('corpus_limit_100_versions')
    return [(v, eligibility(db, v)) for v in versions]
