"""Authenticated admin management; raw streaming body avoids multipart pre-auth spooling."""
import asyncio
from datetime import date
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4
from urllib.parse import unquote
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError, field_validator
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.background import BackgroundTask
from .auth import admin_user, csrf, now
from .database import get_db
from .models import User
from .document_models import Chunk, Document, DocumentVersion, ExtractedPage, IngestionJob, Scheme, VersionRelationship
from .storage import checksum_file, directories, filename_format, original, parser_command, validate_file

router = APIRouter(prefix="/admin/documents", tags=["admin documents"], dependencies=[Depends(admin_user)])


class Metadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=3, max_length=300)
    issuer: str = Field(min_length=2, max_length=200)
    scheme: str | None = Field(default=None, min_length=2, max_length=200)
    document_type: str = Field(default="guidelines", min_length=2, max_length=80)
    source_url: HttpUrl
    language: Literal["en", "hi", "hinglish", "mixed", "unknown"] = "unknown"
    publication_date: date | None = None
    effective_date: date | None = None
    reuse_status: Literal["not_assessed", "local_reference_only", "permission_recorded"] = "not_assessed"
    document_id: UUID | None = None

    @field_validator("source_url")
    @classmethod
    def source_url_check(cls, value):
        if value.username or value.password or len(str(value)) > 1500:
            raise ValueError("Use a source URL without credentials")
        return value


class ArchiveInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    archived: bool


class VerificationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["verified", "rejected"]
    note: str = Field(min_length=20, max_length=2000)


class RelationshipInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    to_version_id: UUID
    kind: Literal["amends", "supersedes"]
    evidence_url: HttpUrl
    scope_note: str = Field(min_length=20, max_length=2000)


def job_data(job):
    return {key: getattr(job, key) for key in ("id", "state", "attempts", "progress", "processed_pages", "total_pages", "error_code", "heartbeat_at", "lease_until", "finished_at")}


def version_data(db, version):
    job = db.scalar(select(IngestionJob).where(IngestionJob.version_id == version.id))
    document = db.get(Document, version.document_id)
    result = {key: getattr(version, key) for key in ("id", "document_id", "version_number", "checksum", "original_name", "format", "size_bytes", "metadata_snapshot", "source_url", "language", "publication_date", "effective_date", "ingested_at", "provenance_status", "verified_at", "verification_note", "extraction_revision", "chunk_profile")}
    result["job"] = job_data(job)
    # Completed extraction does not verify official provenance. Partial/OCR are ineligible.
    from .eligibility import eligibility
    result['eligibility'] = eligibility(db, version)
    result["eligible_for_future_retrieval"] = result['eligibility']['eligible']
    return result


def require_version(db, version_id):
    version = db.get(DocumentVersion, version_id)
    if version is None:
        raise HTTPException(404, "Document version not found")
    return version


def persist_upload(db, settings, temporary, name, format, size, checksum, metadata, user_id):
    snapshot = metadata.model_dump(mode="json", exclude={"document_id"})
    # Serializes dedup/file+DB publication, while extraction occurs outside this short lock.
    db.execute(text("SELECT pg_advisory_xact_lock(28004)"))
    duplicate = db.scalar(select(DocumentVersion).where(DocumentVersion.checksum == checksum))
    if duplicate:
        if duplicate.metadata_snapshot != snapshot or (metadata.document_id and duplicate.document_id != metadata.document_id):
            raise HTTPException(409, "Identical content already exists with different metadata; inspect its version before changing provenance")
        return {"duplicate": True, "version": version_data(db, duplicate)}
    if metadata.document_id:
        document = db.scalar(select(Document).where(Document.id == metadata.document_id).with_for_update())
        if document is None:
            raise HTTPException(404, "Document not found")
        if document.archived_at is not None:
            raise HTTPException(409, "Unarchive document before adding a version")
        if (document.title, document.issuer, document.document_type) != (metadata.title, metadata.issuer, metadata.document_type):
            raise HTTPException(409, "Version must retain its document title, issuer and type")
        scheme_name = db.get(Scheme, document.scheme_id).name if document.scheme_id else None
        if scheme_name != metadata.scheme:
            raise HTTPException(409, "Version must retain its document scheme")
        number = db.scalar(select(func.max(DocumentVersion.version_number)).where(DocumentVersion.document_id == document.id)) + 1
    else:
        scheme = db.scalar(select(Scheme).where(Scheme.name == metadata.scheme)) if metadata.scheme else None
        if metadata.scheme and scheme is None:
            scheme = Scheme(name=metadata.scheme); db.add(scheme); db.flush()
        document = Document(title=metadata.title, issuer=metadata.issuer, document_type=metadata.document_type,
                            scheme_id=scheme.id if scheme else None)
        db.add(document); db.flush()
        number = 1
    version_id = uuid4()
    key = f"{version_id.hex}.{format}"
    destination = original(settings, key)
    # Hard-link publishes atomically and refuses existing targets; never overwrites originals.
    os.link(temporary, destination)
    try:
        version = DocumentVersion(id=version_id, document_id=document.id, version_number=number, checksum=checksum,
            storage_key=key, original_name=name, format=format, size_bytes=size, metadata_snapshot=snapshot,
            source_url=str(metadata.source_url), language=metadata.language, publication_date=metadata.publication_date,
            effective_date=metadata.effective_date, uploaded_by=user_id)
        db.add(version); db.flush()
        db.add(IngestionJob(version_id=version.id)); db.commit()
    except Exception:
        db.rollback()
        # Reconcile handles a process death between filesystem publication and DB commit.
        destination.unlink(missing_ok=True)
        raise
    return {"duplicate": False, "version": version_data(db, version)}


@router.post("/upload", status_code=202, dependencies=[Depends(csrf)])
async def upload(request: Request, filename: str = Query(max_length=180), metadata: str = Header(alias="X-Document-Metadata", max_length=12000),
                 user: User = Depends(admin_user), db: Session = Depends(get_db)):
    format = filename_format(filename)
    try:
        details = Metadata.model_validate_json(unquote(metadata))
    except ValidationError:
        raise HTTPException(422, "Document metadata validation failed") from None
    settings = request.app.state.settings
    temporary = directories(settings) / "temporary" / f"{uuid4().hex}.upload"
    size, checksum = 0, hashlib.sha256()
    try:
        with temporary.open("xb") as file:
            async with asyncio.timeout(60):
                async for data in request.stream():
                    size += len(data)
                    if size > settings.upload_limit_bytes:
                        raise HTTPException(413, "File exceeds the 50 MiB upload limit")
                    checksum.update(data)
                    await run_in_threadpool(file.write, data)
            await run_in_threadpool(file.flush)
            await run_in_threadpool(os.fsync, file.fileno())
        if size == 0:
            raise HTTPException(422, "Empty file")
        await run_in_threadpool(validate_file, settings, temporary, format)
        return await run_in_threadpool(persist_upload, db, settings, temporary, filename, format, size, checksum.hexdigest(), details, user.id)
    except TimeoutError:
        raise HTTPException(408, "Upload exceeded its time limit") from None
    finally:
        temporary.unlink(missing_ok=True)


@router.get("")
def listing(page: int = Query(default=1, ge=1), limit: int = Query(default=20, ge=1, le=50), db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(Document))
    documents = db.scalars(select(Document).order_by(Document.created_at.desc(), Document.id).offset((page - 1) * limit).limit(limit))
    items = []
    for document in documents:
        latest = db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == document.id).order_by(DocumentVersion.version_number.desc()).limit(1))
        items.append({"id": document.id, "title": document.title, "issuer": document.issuer, "archived": document.archived_at is not None,
                      "latest_version": version_data(db, latest)})
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.get("/{document_id}")
def detail(document_id: UUID, page: int = Query(default=1, ge=1), db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(404, "Document not found")
    versions = db.scalars(select(DocumentVersion).where(DocumentVersion.document_id == document_id).order_by(DocumentVersion.version_number.desc()).offset((page - 1) * 20).limit(20))
    return {"id": document.id, "title": document.title, "archived": document.archived_at is not None,
            "versions": [version_data(db, v) for v in versions], "page": page}


@router.patch("/{document_id}/archive", dependencies=[Depends(csrf)])
def archive(document_id: UUID, body: ArchiveInput, db: Session = Depends(get_db)):
    document = db.scalar(select(Document).where(Document.id == document_id).with_for_update())
    if document is None:
        raise HTTPException(404, "Document not found")
    document.archived_at = now() if body.archived else None
    db.commit()
    return {"archived": body.archived}


@router.get("/versions/{version_id}/status")
def status(version_id: UUID, db: Session = Depends(get_db)):
    return version_data(db, require_version(db, version_id))


@router.get("/versions/{version_id}/pages")
def pages(version_id: UUID, page: int = Query(default=1, ge=1), db: Session = Depends(get_db)):
    require_version(db, version_id)
    source = db.scalars(select(ExtractedPage).where(ExtractedPage.version_id == version_id).order_by(ExtractedPage.ordinal).offset((page - 1) * 50).limit(50))
    total = db.scalar(select(func.count()).select_from(ExtractedPage).where(ExtractedPage.version_id == version_id))
    return {"total": total, "page": page, "items": [{"id": p.id, "ordinal": p.ordinal, "pdf_page_number": p.pdf_page_number,
           "source_start": p.source_start, "character_count": len(p.text), "quality_flags": p.quality_flags, "method": p.method} for p in source]}


@router.get("/versions/{version_id}/pages/{ordinal}")
def page_text(version_id: UUID, ordinal: int, offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)):
    require_version(db, version_id)
    page = db.scalar(select(ExtractedPage).where(ExtractedPage.version_id == version_id, ExtractedPage.ordinal == ordinal))
    if page is None:
        raise HTTPException(404, "Extracted page/section not available")
    return {"ordinal": ordinal, "pdf_page_number": page.pdf_page_number, "offset": offset, "source_start": page.source_start,
            "text": page.text[offset:offset + 20000], "total_characters": len(page.text),
            "paragraphs": [p for p in page.paragraphs if p["end"] > offset and p["start"] < offset + 20000], "quality_flags": page.quality_flags}


@router.get("/versions/{version_id}/chunks")
def chunk_list(version_id: UUID, page: int = Query(default=1, ge=1), db: Session = Depends(get_db)):
    require_version(db, version_id)
    rows = db.scalars(select(Chunk).where(Chunk.version_id == version_id).order_by(Chunk.ordinal).offset((page - 1) * 50).limit(50))
    return {"items": [{key: getattr(c, key) for key in ("id", "page_id", "ordinal", "start_offset", "end_offset", "text", "section_label", "continued_clause", "profile")} for c in rows], "page": page}


@router.post("/versions/{version_id}/retry", dependencies=[Depends(csrf)])
def retry(version_id: UUID, db: Session = Depends(get_db)):
    version = require_version(db, version_id)
    job = db.scalar(select(IngestionJob).where(IngestionJob.version_id == version_id).with_for_update())
    if db.get(Document, version.document_id).archived_at is not None:
        raise HTTPException(409, "Unarchive document before retry")
    if job.state != "failed" or job.attempts >= 3:
        raise HTTPException(409, "Only failed jobs with fewer than three attempts can retry; OCR awaits Part 7")
    job.state, job.progress, job.error_code, job.finished_at = "queued", 0, None, None
    db.commit()
    return job_data(job)


@router.patch("/versions/{version_id}/provenance", dependencies=[Depends(csrf)])
def provenance(version_id: UUID, body: VerificationInput, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    version = db.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id).with_for_update())
    if version is None:
        raise HTTPException(404, "Document version not found")
    if version.provenance_status != "unverified":
        raise HTTPException(409, "Provenance decision already recorded; amendment of verification requires later audit workflow")
    version.provenance_status, version.verification_note = body.status, body.note
    version.verified_at, version.verified_by = now(), user.id
    db.commit()
    return version_data(db, version)


@router.post("/versions/{version_id}/relationships", dependencies=[Depends(csrf)], status_code=201)
def relationship(version_id: UUID, body: RelationshipInput, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    # Serialize supersession with final citation/source publication locks.
    list(db.scalars(select(DocumentVersion).where(DocumentVersion.id.in_([version_id,body.to_version_id])).order_by(DocumentVersion.id).with_for_update()))
    source, target = require_version(db, version_id), require_version(db, body.to_version_id)
    if source.id == target.id or source.provenance_status != "verified" or target.provenance_status != "verified":
        raise HTTPException(409, "Relationships require distinct verified source versions")
    if db.scalar(select(VersionRelationship).where(VersionRelationship.from_version_id == source.id,
            VersionRelationship.to_version_id == target.id, VersionRelationship.kind == body.kind)):
        raise HTTPException(409, "Relationship already recorded")
    record = VersionRelationship(from_version_id=source.id, to_version_id=target.id, kind=body.kind,
            evidence_url=str(body.evidence_url), scope_note=body.scope_note, verified_by=user.id)
    db.add(record); db.commit()
    return {"id": record.id, "kind": record.kind, "scope_note": record.scope_note}


@router.get("/versions/{version_id}/relationships")
def relationships(version_id: UUID, page: int = Query(default=1, ge=1), db: Session = Depends(get_db)):
    require_version(db, version_id)
    records = db.scalars(select(VersionRelationship).where((VersionRelationship.from_version_id == version_id) |
        (VersionRelationship.to_version_id == version_id)).order_by(VersionRelationship.verified_at, VersionRelationship.id)
        .offset((page - 1) * 20).limit(20))
    return {"page": page, "items": [{key: getattr(record, key) for key in
        ('id', 'from_version_id', 'to_version_id', 'kind', 'evidence_url', 'scope_note', 'verified_at')} for record in records]}


@router.get("/versions/{version_id}/original")
def download(version_id: UUID, request: Request, db: Session = Depends(get_db)):
    version = require_version(db, version_id)
    path = original(request.app.state.settings, version.storage_key)
    if not path.is_file():
        raise HTTPException(404, "Original file unavailable")
    if path.stat().st_size != version.size_bytes or checksum_file(path) != version.checksum:
        raise HTTPException(409, "Original integrity check failed")
    return FileResponse(path, filename=f"source-{version.id}.{version.format}",
                        media_type="application/pdf" if version.format == "pdf" else "text/plain; charset=utf-8",
                        headers={"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox; default-src 'none'"})


@router.get("/versions/{version_id}/preview/{ordinal}")
def preview(version_id: UUID, ordinal: int, request: Request, db: Session = Depends(get_db)):
    version = require_version(db, version_id)
    settings = request.app.state.settings
    path = original(settings, version.storage_key)
    if version.format != "pdf" or not path.is_file() or checksum_file(path) != version.checksum:
        raise HTTPException(409, "PDF preview unavailable or original integrity failed")
    output = directories(settings) / 'temporary' / f'{uuid4().hex}.png'
    command, environment = parser_command(settings, path, 'pdf', output)
    command.extend(['--render-page', str(ordinal)])
    try:
        result = subprocess.run(command, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=settings.parser_seconds, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode or not output.exists() or output.stat().st_size > 10 * 1024 * 1024 or output.open('rb').read(8) != b'\x89PNG\r\n\x1a\n':
            raise HTTPException(422, "Bounded PDF page preview failed")
        return FileResponse(output, media_type='image/png', headers={'X-Content-Type-Options': 'nosniff'},
                            background=BackgroundTask(output.unlink, missing_ok=True))
    except Exception as error:
        output.unlink(missing_ok=True)
        if isinstance(error, HTTPException): raise
        raise HTTPException(422, "Bounded PDF page preview failed") from None
