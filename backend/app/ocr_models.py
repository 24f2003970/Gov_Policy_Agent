"""Additive extraction revisions; original digital pages and historical spans stay intact."""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import CheckConstraint, ForeignKey, String, Text, Integer, DateTime, Index, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base


class ExtractionRevision(Base):
    __tablename__ = 'extraction_revisions'
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version_id: Mapped[UUID] = mapped_column(ForeignKey('document_versions.id'), index=True)
    creator_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    state: Mapped[str] = mapped_column(String(20), default='queued')
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    spec: Mapped[dict] = mapped_column(JSONB)
    processed: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer)
    lease_owner: Mapped[UUID | None] = mapped_column(nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        CheckConstraint("state IN ('queued','processing','pending_review','completed','partial','failed','cancelled') AND attempts BETWEEN 0 AND 3 AND processed >= 0 AND total > 0", name='ck_ocr_job'),
        Index('ix_ocr_pending_version', 'version_id', unique=True, postgresql_where=text("state IN ('queued','processing','pending_review')")),)


class ExtractionPage(Base):
    __tablename__ = 'extraction_pages'
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    revision_id: Mapped[UUID] = mapped_column(ForeignKey('extraction_revisions.id'), index=True)
    page_id: Mapped[UUID] = mapped_column(ForeignKey('extracted_pages.id'))
    attempt: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    paragraphs: Mapped[list] = mapped_column(JSONB)
    method: Mapped[str] = mapped_column(String(20))
    quality_flags: Mapped[list] = mapped_column(JSONB)
    signals: Mapped[dict] = mapped_column(JSONB)
    boxes: Mapped[list] = mapped_column(JSONB)
    __table_args__ = (UniqueConstraint('revision_id','page_id','attempt'),
        CheckConstraint("method IN ('digital','ocr','failed') AND attempt BETWEEN 0 AND 3", name='ck_ocr_page'),)


class ExtractionReview(Base):
    __tablename__ = 'extraction_reviews'
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    page_id: Mapped[UUID] = mapped_column(ForeignKey('extraction_pages.id'), index=True)
    reviewer_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    decision: Mapped[str] = mapped_column(String(10))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (CheckConstraint("decision IN ('accepted','rejected')", name='ck_ocr_review'),)


class ExtractionState(Base):
    __tablename__ = 'extraction_state'
    version_id: Mapped[UUID] = mapped_column(ForeignKey('document_versions.id'), primary_key=True)
    ready_id: Mapped[UUID] = mapped_column(ForeignKey('extraction_revisions.id'))
