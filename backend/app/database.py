"""Synchronous database access runs in FastAPI's worker threads."""
from sqlalchemy import URL, create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from fastapi import Request

from .config import Settings

SCHEMA_HEAD = "0009_answer_feedback"


def database_url(settings: Settings, test: bool = False):
    password = settings.test_db_password if test else settings.db_password
    if password is None:
        raise ValueError("Database configuration missing; run private configure command")
    # URL.create safely handles @, %, :, / etc. No manually escaped DSN needed.
    return URL.create("postgresql+psycopg", username=settings.test_db_user if test else settings.db_user,
                      password=password.get_secret_value(), host=settings.db_host, port=settings.db_port,
                      database=settings.test_db_name if test else settings.db_name)


def make_engine(settings: Settings, test: bool = False):
    return create_engine(database_url(settings, test), pool_size=3, max_overflow=2,
                         pool_timeout=2, pool_pre_ping=True, hide_parameters=True,
                         connect_args={"connect_timeout": 2,
                                       "options": "-c statement_timeout=2000 -c lock_timeout=2000"})


def install_database(app, settings: Settings):
    app.state.engine = make_engine(settings) if settings.db_password is not None else None
    app.state.sessions = sessionmaker(app.state.engine, expire_on_commit=False) if app.state.engine else None


def schema_ready(engine) -> bool:
    if engine is None:
        return False
    try:
        with engine.connect() as connection:
            if connection.scalar(text("SELECT version_num FROM alembic_version")) != SCHEMA_HEAD:
                return False
            # Required columns must exist, not just a forged migration marker.
            connection.execute(text("SELECT id, email, username, password_hash, role, active, preferred_language, created_at, updated_at FROM users LIMIT 0"))
            connection.execute(text("SELECT id, user_id, refresh_hash, used_hashes, expires_at, revoked_at, rotated_at, created_at FROM auth_sessions LIMIT 0"))
            connection.execute(text("SELECT key, attempts, window_start FROM auth_throttles LIMIT 0"))
            connection.execute(text("SELECT id, document_id, checksum, storage_key, provenance_status FROM document_versions LIMIT 0"))
            connection.execute(text("SELECT id, version_id, state, lease_owner, lease_until, attempts FROM ingestion_jobs LIMIT 0"))
            connection.execute(text("SELECT id, version_id, ordinal, pdf_page_number, text FROM extracted_pages LIMIT 0"))
            connection.execute(text("SELECT id, version_id, page_id, start_offset, end_offset FROM chunks LIMIT 0"))
            connection.execute(text("SELECT id, decision, reuse_status, evidence_url FROM eligibility_reviews LIMIT 0"))
            connection.execute(text("SELECT id, state, spec, versions, lease_owner FROM index_generations LIMIT 0"))
            connection.execute(text("SELECT id, generation_id, page_id, start_offset, end_offset FROM index_passages LIMIT 0"))
            connection.execute(text("SELECT id, active_id FROM index_state LIMIT 0"))
            connection.execute(text("SELECT id, user_id, question, state, result, sources, evidence_quality FROM answer_runs LIMIT 0"))
            connection.execute(text("SELECT id, heartbeat FROM answer_worker LIMIT 0"))
            connection.execute(text("SELECT id, run_id, position, retained, assessment FROM answer_claims LIMIT 0"))
            connection.execute(text("SELECT id, claim_id, passage_id, page_id, quote FROM claim_citations LIMIT 0"))
            connection.execute(text("SELECT id, revision_id, text, boxes FROM extraction_pages LIMIT 0"))
            connection.execute(text("SELECT id, lease_owner, state FROM extraction_revisions LIMIT 0"))
            connection.execute(text("SELECT id, page_id, decision FROM extraction_reviews LIMIT 0"))
            connection.execute(text("SELECT version_id, ready_id FROM extraction_state LIMIT 0"))
            connection.execute(text("SELECT user_id, run_id, created_at FROM saved_answers LIMIT 0"))
            connection.execute(text("SELECT user_id, run_id, vote, reason, comment, updated_at FROM answer_feedback LIMIT 0"))
            return True
    except SQLAlchemyError:
        return False


def get_db(request: Request):
    if request.app.state.sessions is None:
        from fastapi import HTTPException
        raise HTTPException(503, "Database is not configured")
    with request.app.state.sessions() as session:
        yield session
