"""Immutable-by-API claim/citation snapshots; no backfill of old answers."""
from datetime import datetime
from uuid import UUID
from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, DateTime, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base


class AnswerClaim(Base):
    __tablename__ = 'answer_claims'
    id: Mapped[UUID] = mapped_column(primary_key=True)
    run_id: Mapped[UUID] = mapped_column(ForeignKey('answer_runs.id',ondelete='CASCADE'),index=True)
    position: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    retained: Mapped[bool]
    assessment: Mapped[dict] = mapped_column(JSONB)
    snapshot: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())
    __table_args__ = (UniqueConstraint('run_id','position'),CheckConstraint('position >= 1',name='ck_claim_position'))


class ClaimCitation(Base):
    __tablename__ = 'claim_citations'
    id: Mapped[UUID] = mapped_column(primary_key=True)
    claim_id: Mapped[UUID] = mapped_column(ForeignKey('answer_claims.id',ondelete='CASCADE'),index=True)
    position: Mapped[int] = mapped_column(Integer)
    version_id: Mapped[UUID] = mapped_column(ForeignKey('document_versions.id'))
    passage_id: Mapped[UUID] = mapped_column(ForeignKey('index_passages.id'))
    page_id: Mapped[UUID] = mapped_column(ForeignKey('extracted_pages.id'))
    quote: Mapped[str] = mapped_column(Text)
    start_offset: Mapped[int] = mapped_column(Integer)
    end_offset: Mapped[int] = mapped_column(Integer)
    metadata_snapshot: Mapped[dict] = mapped_column(JSONB)
    provenance: Mapped[dict] = mapped_column(JSONB)
    __table_args__ = (UniqueConstraint('claim_id','position'),CheckConstraint('start_offset >= 0 AND end_offset > start_offset',name='ck_citation_span'))
