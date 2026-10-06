"""Owned bounded answer jobs and private grounding snapshots; no raw model traces."""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, UniqueConstraint, String, Text, DateTime, Boolean, Integer, Index, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base


class AnswerRun(Base):
    __tablename__ = 'answer_runs'
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'), index=True)
    question: Mapped[str] = mapped_column(Text)
    retrieval_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    query_normalization: Mapped[dict] = mapped_column(JSONB, default=dict)
    language: Mapped[str] = mapped_column(String(2))
    filters: Mapped[dict] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(16), default='queued')
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sources: Mapped[list] = mapped_column(JSONB, default=list)
    model: Mapped[dict] = mapped_column(JSONB, default=dict)
    timings: Mapped[dict] = mapped_column(JSONB, default=dict)
    evidence_quality: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        UniqueConstraint('user_id','id',name='uq_answer_owner_id'),
        CheckConstraint("state IN ('queued','processing','done','error','cancelled') AND language IN ('en','hi')",name='ck_answer_state'),
        Index('ix_single_pending_answer', text('(1)'), unique=True, postgresql_where=text("state IN ('queued','processing')")),
    )


class AnswerWorker(Base):
    __tablename__ = 'answer_worker'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    heartbeat: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint('id = 1',name='ck_answer_worker_single'),)


class SavedAnswer(Base):
    __tablename__ = 'saved_answers'
    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    run_id: Mapped[UUID] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())
    __table_args__ = (ForeignKeyConstraint(['user_id','run_id'],['answer_runs.user_id','answer_runs.id'],ondelete='CASCADE'),)


class AnswerFeedback(Base):
    __tablename__ = 'answer_feedback'
    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    run_id: Mapped[UUID] = mapped_column(primary_key=True)
    vote: Mapped[str] = mapped_column(String(12))
    reason: Mapped[str | None] = mapped_column(String(24), nullable=True)
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())
    __table_args__ = (
        ForeignKeyConstraint(['user_id','run_id'],['answer_runs.user_id','answer_runs.id'],ondelete='CASCADE'),
        CheckConstraint("vote IN ('helpful','not_helpful')",name='ck_feedback_vote'),
        CheckConstraint("reason IS NULL OR reason IN ('unclear_wording','incomplete_answer','citation_issue','language_issue','suspected_factual_error')",name='ck_feedback_reason'),
    )
