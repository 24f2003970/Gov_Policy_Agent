"""Real PostgreSQL plus real parser child processes; synthetic fixtures, isolated storage."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import os
import subprocess
import sys
from uuid import UUID
from urllib.parse import quote
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pymupdf
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker
from app.auth import now
from app.main import create_app
from app.models import User, AuthSession
from app.document_models import Document, DocumentVersion, ExtractedPage, Chunk, IngestionJob
from app.ingestion import claim, finish, heartbeat, process_claim, reconcile, run_once
from app.storage import original, directories
from test_auth_postgres import postgres, ORIGIN, REG, signup_login, auth_header, migrate

META = {"title": "Synthetic policy for tests", "issuer": "Synthetic test issuer", "source_url": "https://example.gov.in/test.pdf", "language": "en", "reuse_status": "permission_recorded"}


def pdf(pages=('Section 1 Eligibility\nSynthetic policy: conditions and exclusions apply.\n',), encrypted=False):
    document = pymupdf.open()
    for content in pages:
        page = document.new_page()
        if content:
            page.insert_text((40, 40), content)
    kwargs = dict(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw='test-owner-only', user_pw='test-user-only') if encrypted else {}
    data = document.tobytes(**kwargs)
    document.close()
    return data


@pytest.fixture
def docs(postgres, tmp_path):
    settings, engine = postgres
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE index_state, index_passages, index_generations, eligibility_reviews, auth_throttles, auth_sessions, chunks, version_relationships, ingestion_jobs, extracted_pages, document_versions, documents, schemes, users CASCADE"))
    settings = settings.model_copy(update={"data_dir": tmp_path, "environment": "test"})
    app = create_app(settings)
    app.state.engine.dispose(); app.state.engine = engine
    app.state.sessions = sessionmaker(engine, expire_on_commit=False)
    with TestClient(app, base_url='http://127.0.0.1:8000') as client:
        tokens, _ = signup_login(client)
        normal = {**ORIGIN, **auth_header(tokens['access_token'])}
        with Session(engine) as db:
            user = db.scalar(select(User)); user.role = 'admin'; db.commit()
        yield client, settings, engine, normal


def upload(docs, data, name='policy.pdf', metadata=None, headers=None):
    client, _, _, admin = docs
    request_headers = dict(headers or {**admin, 'Content-Type': 'application/octet-stream'})
    request_headers['X-Document-Metadata'] = quote(json.dumps(metadata or META))
    return client.post('/admin/documents/upload', params={'filename': name}, headers=request_headers, content=data)


def status(docs, version):
    client, _, _, headers = docs
    return client.get(f'/admin/documents/versions/{version}/status', headers=headers).json()


def test_digital_pdf_spans_dedup_and_protected_original(docs):
    client, settings, engine, headers = docs
    data = pdf(('Section 1 Eligibility\nAll conditions apply; no automatic entitlement.', 'Clause 2 Exclusions\nRead this second page carefully.'))
    response = upload(docs, data)
    assert response.status_code == 202
    version = response.json()['version']['id']
    assert 'storage_key' not in response.text and str(settings.data_dir) not in response.text
    assert run_once(engine, settings)
    assert status(docs, version)['job']['state'] == 'completed'
    assert not status(docs, version)['eligible_for_future_retrieval']
    duplicate = upload(docs, data)
    assert duplicate.json()['duplicate'] and duplicate.json()['version']['id'] == version
    assert upload(docs, data, metadata={**META, 'title': 'Conflicting metadata'}).status_code == 409
    with Session(engine) as db:
        pages = list(db.scalars(select(ExtractedPage).order_by(ExtractedPage.ordinal)))
        assert [p.pdf_page_number for p in pages] == [1, 2]
        with pymupdf.open(stream=data, filetype='pdf') as original_pdf:
            assert [p.text for p in pages] == [p.get_text('text', sort=False) for p in original_pdf]
        for chunk in db.scalars(select(Chunk)):
            page = db.get(ExtractedPage, chunk.page_id)
            assert chunk.text == page.text[chunk.start_offset:chunk.end_offset]
        assert db.scalar(select(func.count()).select_from(IngestionJob)) == 1
    assert client.get(f'/admin/documents/versions/{version}/original').status_code == 401
    downloaded = client.get(f'/admin/documents/versions/{version}/original', headers=headers)
    assert downloaded.content == data and downloaded.headers['x-content-type-options'] == 'nosniff'
    assert client.get(f'/admin/documents/versions/{version}/pages', headers=headers).json()['total'] == 2
    assert client.post(f'/admin/documents/versions/{version}/retry', headers=headers).status_code == 409


def test_txt_exact_offsets_chunks_and_safe_content(docs):
    client, settings, engine, headers = docs
    content = 'Section 1 Eligibility\n' + ('Conditions apply. हिन्दी policy example.\n' * 100) + '\n<script>alert(1)</script>\r\n'
    version = upload(docs, content.encode(), 'safe.txt').json()['version']['id']
    assert run_once(engine, settings)
    with Session(engine) as db:
        page = db.scalar(select(ExtractedPage))
        assert page.pdf_page_number is None and page.text == content
        rows = list(db.scalars(select(Chunk).order_by(Chunk.ordinal)))
        covered = set()
        for chunk in rows:
            assert chunk.text == content[chunk.start_offset:chunk.end_offset]
            covered.update(range(chunk.start_offset, chunk.end_offset))
        assert covered == set(range(len(content)))
        assert any(c.continued_clause for c in rows)
    result = client.get(f'/admin/documents/versions/{version}/pages/1', headers=headers).json()
    assert result['text'] == content
    assert client.get(f'/admin/documents/versions/{version}/original', headers=headers).headers['content-type'].startswith('text/plain')


@pytest.mark.parametrize('data,name', [(b'not a PDF', 'bad.pdf'), (b'%PDF-broken', 'bad.pdf'), (pdf(encrypted=True), 'locked.pdf'), (pdf(), 'wrong.txt'), (b'\xff\xfe\x00', 'bad.txt'), (b'', 'empty.txt'), (b'plain text', 'bad.docx'), (b'plain text', '../bad.txt')])
def test_invalid_files_rejected_without_published_results(docs, data, name):
    response = upload(docs, data, name)
    assert response.status_code in {415, 422}
    _, settings, engine, _ = docs
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(DocumentVersion)) == 0
    assert not list((directories(settings) / 'originals').iterdir())
    assert not list((directories(settings) / 'temporary').iterdir())


def test_size_limit_on_stream_ignores_claimed_length(docs):
    client, settings, _, headers = docs
    client.app.state.settings = settings.model_copy(update={'upload_limit_bytes': 100})
    response = upload(docs, b'a' * 101, 'large.txt', headers={**headers, 'Content-Length': '1'})
    assert response.status_code == 413


@pytest.mark.parametrize('pages,state', [(('',), 'needs_ocr'), (('Text policy conditions and exclusions. Read carefully.', ''), 'partial')])
def test_scanned_and_mixed_pdf(docs, pages, state):
    _, settings, engine, _ = docs
    version = upload(docs, pdf(pages)).json()['version']['id']
    assert run_once(engine, settings)
    value = status(docs, version)
    assert value['job']['state'] == state and not value['eligible_for_future_retrieval']
    with Session(engine) as db:
        assert any('needs_ocr' in p.quality_flags for p in db.scalars(select(ExtractedPage)))


def test_normal_user_unauthenticated_and_csrf_denial(docs):
    client, _, engine, headers = docs
    data = pdf()
    assert upload(docs, data, headers=ORIGIN).status_code == 401
    with Session(engine) as db:
        user = db.scalar(select(User)); user.role = 'user'; db.commit()
    assert upload(docs, data).status_code == 403
    with Session(engine) as db:
        user = db.scalar(select(User)); user.role = 'admin'; db.commit()
    assert upload(docs, data, headers=auth_header(headers['Authorization'].split()[1])).status_code == 403


def test_failed_retry_and_atomic_result_publication(docs):
    client, settings, engine, headers = docs
    data = pdf()
    version = upload(docs, data).json()['version']['id']
    with Session(engine) as db:
        record = db.get(DocumentVersion, UUID(version)); path = original(settings, record.storage_key)
    path.write_bytes(b'changed')
    assert run_once(engine, settings)
    assert status(docs, version)['job']['state'] == 'failed'
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(ExtractedPage)) == 0
    path.write_bytes(data)
    assert client.post(f'/admin/documents/versions/{version}/retry', headers=headers).status_code == 200
    assert run_once(engine, settings)
    assert status(docs, version)['job']['state'] == 'completed'
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(ExtractedPage)) == 1


def test_lease_recovery_concurrency_fencing_attempt_limit(docs):
    _, settings, engine, _ = docs
    version = upload(docs, pdf()).json()['version']['id']
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: claim(engine, settings), range(2)))
    first = next(result for result in results if result is not None)
    assert sum(result is not None for result in results) == 1
    assert heartbeat(engine, settings, first[0], first[1])
    with Session(engine) as db:
        db.get(IngestionJob, first[0]).lease_until = now() - timedelta(seconds=1); db.commit()
    second = claim(engine, settings)
    assert second and second[1] != first[1]
    assert not finish(engine, first[0], first[1], {'error': 'stale_worker'})
    assert process_claim(engine, settings, second)
    assert status(docs, version)['job']['attempts'] == 2


def test_real_worker_process_termination_and_restart(docs):
    _, settings, engine, _ = docs
    version = upload(docs, pdf()).json()['version']['id']
    # A real process claims the actual persisted job then waits; parent terminates it.
    script = 'import sys,time;sys.path.insert(0,"backend");from app.config import Settings;from app.database import make_engine;from app.ingestion import claim;s=Settings();e=make_engine(s,test=True);assert claim(e,s);print("claimed",flush=True);time.sleep(120)'
    process = subprocess.Popen([sys.executable, '-c', script], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    try:
        assert process.stdout.readline().strip() == 'claimed'
        process.terminate(); process.wait(timeout=10)
        with Session(engine) as db:
            job = db.scalar(select(IngestionJob)); job.lease_until = now() - timedelta(seconds=1); db.commit()
        assert run_once(engine, settings)
        assert status(docs, version)['job']['state'] == 'completed'
    finally:
        if process.poll() is None: process.kill(); process.wait()


def test_archive_provenance_versions_and_immutability(docs):
    client, settings, engine, headers = docs
    first = upload(docs, pdf()).json()['version']
    doc_id = first['document_id']
    assert client.patch(f'/admin/documents/{doc_id}/archive', headers=headers, json={'archived': True}).status_code == 200
    assert not run_once(engine, settings)
    assert client.patch(f'/admin/documents/{doc_id}/archive', headers=headers, json={'archived': False}).status_code == 200
    assert run_once(engine, settings)
    second = upload(docs, pdf(('Section 1 Revised eligibility\nSynthetic second version with more conditions.',)), metadata={**META, 'document_id': doc_id}).json()['version']
    assert second['version_number'] == 2
    assert run_once(engine, settings)
    for v in (first, second):
        result = client.patch(f"/admin/documents/versions/{v['id']}/provenance", headers=headers,
             json={'status': 'verified', 'note': 'Synthetic test provenance decision, not a real official source'})
        assert result.status_code == 200 and not result.json()['eligible_for_future_retrieval']
        assert 'audit_review_required' in result.json()['eligibility']['reasons']
    result = client.post(f"/admin/documents/versions/{second['id']}/relationships", headers=headers,
        json={'to_version_id': first['id'], 'kind': 'amends', 'evidence_url': 'https://example.gov.in/amendment', 'scope_note': 'Synthetic test scope only, explicitly confirmed by tester'})
    assert result.status_code == 201
    records = client.get(f"/admin/documents/versions/{second['id']}/relationships", headers=headers).json()['items']
    assert len(records) == 1 and records[0]['kind'] == 'amends'
    with engine.begin() as connection:
        with pytest.raises(DBAPIError):
            connection.execute(text("UPDATE document_versions SET source_url='https://changed.example'"))


def test_orphan_reconcile_preserves_referenced_and_recent_files(docs):
    _, settings, engine, _ = docs
    upload(docs, pdf())
    root = directories(settings)
    orphan = root / 'originals' / ('f' * 32 + '.pdf'); orphan.write_bytes(b'orphan')
    temporary = root / 'temporary' / ('e' * 32 + '.upload'); temporary.write_bytes(b'recent')
    os.utime(orphan, (0, 0))
    assert reconcile(engine, settings) == 1
    assert temporary.exists() and len(list((root / 'originals').iterdir())) == 1


def test_upgrade_preserves_auth_users_sessions(docs):
    client, _, engine, headers = docs
    config = Config(str(Path('backend/alembic.ini').resolve()))
    with Session(engine) as db:
        before_users = list(db.execute(select(User.id, User.password_hash, User.role)))
        before_sessions = list(db.execute(select(AuthSession.id, AuthSession.refresh_hash)))
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.downgrade(config, '0001_auth')
        command.upgrade(config, 'head')
    with Session(engine) as db:
        assert list(db.execute(select(User.id, User.password_hash, User.role))) == before_users
        assert list(db.execute(select(AuthSession.id, AuthSession.refresh_hash))) == before_sessions
    assert client.get('/auth/me', headers=headers).status_code == 200


def test_protected_preview_and_original_integrity(docs):
    client, settings, engine, headers = docs
    version = upload(docs, pdf()).json()['version']['id']
    path = f'/admin/documents/versions/{version}/preview/1'
    assert client.get(path).status_code == 401
    response = client.get(path, headers=headers)
    assert response.status_code == 200 and response.content.startswith(b'\x89PNG\r\n\x1a\n')
    assert not list((directories(settings) / 'temporary').iterdir())
    assert client.get(path.rsplit('/', 1)[0] + '/999', headers=headers).status_code == 422
    with Session(engine) as db:
        record = db.get(DocumentVersion, UUID(version)); original(settings, record.storage_key).write_bytes(b'changed')
    assert client.get(f'/admin/documents/versions/{version}/original', headers=headers).status_code == 409


def test_parser_page_text_and_time_limits(docs):
    client, settings, _, _ = docs
    client.app.state.settings = settings.model_copy(update={'max_pages': 1})
    assert upload(docs, pdf(('first page', 'second page'))).status_code == 422
    client.app.state.settings = settings.model_copy(update={'max_text_chars': 100})
    assert upload(docs, b'x' * 101, 'limited.txt').status_code == 422
    # Actual child startup is killed by a deliberately tiny test timeout, no mocked success.
    client.app.state.settings = settings.model_copy(update={'parser_seconds': 0.001})
    assert upload(docs, pdf()).status_code == 422


def test_result_transaction_rolls_back_and_attempts_are_bounded(docs):
    _, settings, engine, _ = docs
    upload(docs, pdf())
    first = claim(engine, settings)
    page = {'ordinal': 1, 'pdf_page_number': 1, 'source_start': 0, 'text': 'Synthetic example text',
            'paragraphs': [], 'quality_flags': [], 'method': 'synthetic-test'}
    with pytest.raises(DBAPIError):
        finish(engine, first[0], first[1], {'pages': [page, page]})  # Unique ordinal failure after first page insert.
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(ExtractedPage)) == 0
        assert db.scalar(select(func.count()).select_from(Chunk)) == 0
        job = db.get(IngestionJob, first[0]); job.attempts = 3; job.lease_until = now() - timedelta(seconds=1); db.commit()
    assert claim(engine, settings) is None
    with Session(engine) as db:
        assert db.get(IngestionJob, first[0]).state == 'failed'


def test_local_reference_rights_never_retrieval_ready(docs):
    client, settings, engine, headers = docs
    version = upload(docs, pdf(), metadata={**META, 'reuse_status': 'local_reference_only'}).json()['version']['id']
    assert run_once(engine, settings)
    response = client.patch(f'/admin/documents/versions/{version}/provenance', headers=headers,
        json={'status': 'verified', 'note': 'Origin verified, local reference only. No reproduction permission granted.'})
    assert response.status_code == 200 and not response.json()['eligible_for_future_retrieval']
