"""Part 3 source provenance and durable ingestion; no embeddings or answers."""
from datetime import date, datetime
from uuid import UUID, uuid4
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .models import Base


class Scheme(Base):
    __tablename__ = "schemes"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    scheme_id: Mapped[UUID | None] = mapped_column(ForeignKey("schemes.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    issuer: Mapped[str] = mapped_column(String(200))
    document_type: Mapped[str] = mapped_column(String(80))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number"),
        CheckConstraint("version_number > 0 AND size_bytes > 0", name="ck_version_numbers"),
        CheckConstraint("format IN ('pdf','txt')", name="ck_version_format"),
        CheckConstraint("provenance_status IN ('unverified','verified','rejected')", name="ck_provenance_status"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    checksum: Mapped[str] = mapped_column(String(64), unique=True)
    storage_key: Mapped[str] = mapped_column(String(40), unique=True)
    original_name: Mapped[str] = mapped_column(String(180))
    format: Mapped[str] = mapped_column(String(3))
    size_bytes: Mapped[int] = mapped_column(Integer)
    metadata_snapshot: Mapped[dict] = mapped_column(JSONB)
    source_url: Mapped[str] = mapped_column(String(1500))
    language: Mapped[str] = mapped_column(String(20))
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    uploaded_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    provenance_status: Mapped[str] = mapped_column(String(12), default="unverified", server_default="unverified")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    verification_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_revision: Mapped[str | None] = mapped_column(String(80), nullable=True)
    chunk_profile: Mapped[str | None] = mapped_column(String(80), nullable=True)


class VersionRelationship(Base):
    __tablename__ = "version_relationships"
    __table_args__ = (
        UniqueConstraint("from_version_id", "to_version_id", "kind"),
        CheckConstraint("from_version_id <> to_version_id", name="ck_relationship_distinct"),
        CheckConstraint("kind IN ('amends','supersedes')", name="ck_relationship_kind"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    from_version_id: Mapped[UUID] = mapped_column(ForeignKey("document_versions.id"), index=True)
    to_version_id: Mapped[UUID] = mapped_column(ForeignKey("document_versions.id"))
    kind: Mapped[str] = mapped_column(String(12))
    evidence_url: Mapped[str] = mapped_column(String(1500))
    scope_note: Mapped[str] = mapped_column(Text)
    verified_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExtractedPage(Base):
    __tablename__ = "extracted_pages"
    __table_args__ = (
        UniqueConstraint("version_id", "ordinal"),
        CheckConstraint("ordinal > 0 AND (pdf_page_number IS NULL OR pdf_page_number > 0)", name="ck_page_number"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version_id: Mapped[UUID] = mapped_column(ForeignKey("document_versions.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    pdf_page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_start: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)
    paragraphs: Mapped[list] = mapped_column(JSONB)
    quality_flags: Mapped[list] = mapped_column(JSONB)
    method: Mapped[str] = mapped_column(String(80))


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("version_id", "ordinal"),
        CheckConstraint("start_offset >= 0 AND end_offset > start_offset", name="ck_chunk_offsets"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version_id: Mapped[UUID] = mapped_column(ForeignKey("document_versions.id"), index=True)
    page_id: Mapped[UUID] = mapped_column(ForeignKey("extracted_pages.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    start_offset: Mapped[int] = mapped_column(Integer)
    end_offset: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    section_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    continued_clause: Mapped[bool]
    profile: Mapped[str] = mapped_column(String(80))


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        CheckConstraint("state IN ('queued','processing','completed','needs_ocr','partial','failed')", name="ck_job_state"),
        CheckConstraint("attempts BETWEEN 0 AND 3 AND progress BETWEEN 0 AND 100", name="ck_job_bounds"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version_id: Mapped[UUID] = mapped_column(ForeignKey("document_versions.id"), unique=True)
    state: Mapped[str] = mapped_column(String(12), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    processed_pages: Mapped[int] = mapped_column(Integer, default=0)
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    lease_owner: Mapped[UUID | None] = mapped_column(nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
