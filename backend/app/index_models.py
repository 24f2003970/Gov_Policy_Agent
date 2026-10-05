"""Append-only eligibility decisions and generation-scoped derived indexing records."""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base


class EligibilityReview(Base):
    __tablename__ = 'eligibility_reviews'
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version_id: Mapped[UUID] = mapped_column(ForeignKey('document_versions.id'), index=True)
    reviewer_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    decision: Mapped[str] = mapped_column(String(20))
    reuse_status: Mapped[str] = mapped_column(String(30))
    applicability: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(Text)
    evidence_url: Mapped[str] = mapped_column(String(1500))
    scope: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (CheckConstraint("decision IN ('verified','rejected') AND reuse_status IN ('permission_recorded','local_reference_only','not_assessed') AND applicability IN ('historical','unknown','current_verified')", name='ck_review_choices'),)


class IndexGeneration(Base):
    __tablename__ = 'index_generations'
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    state: Mapped[str] = mapped_column(String(20), default='queued', index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    spec: Mapped[dict] = mapped_column(JSONB)
    versions: Mapped[list] = mapped_column(JSONB)
    processed: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    lease_owner: Mapped[UUID | None] = mapped_column(nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (CheckConstraint("state IN ('queued','processing','ready','failed') AND attempts BETWEEN 0 AND 3 AND processed >= 0 AND total >= 0", name='ck_index_job'),)


class IndexPassage(Base):
    __tablename__ = 'index_passages'
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    generation_id: Mapped[UUID] = mapped_column(ForeignKey('index_generations.id'), index=True)
    version_id: Mapped[UUID] = mapped_column(ForeignKey('document_versions.id'), index=True)
    page_id: Mapped[UUID] = mapped_column(ForeignKey('extracted_pages.id'), index=True)
    start_offset: Mapped[int] = mapped_column(Integer)
    end_offset: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    section_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    continued_clause: Mapped[bool]
    profile: Mapped[str] = mapped_column(String(80))
    __table_args__ = (CheckConstraint('start_offset >= 0 AND end_offset > start_offset', name='ck_index_span'),)


class IndexState(Base):
    __tablename__ = 'index_state'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    active_id: Mapped[UUID | None] = mapped_column(ForeignKey('index_generations.id'), nullable=True)
    __table_args__ = (CheckConstraint('id = 1', name='ck_single_index'),)
