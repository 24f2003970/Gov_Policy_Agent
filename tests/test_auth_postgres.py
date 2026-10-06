"""Required real PostgreSQL tests. Missing PostgreSQL/config is a failure, not a fake pass."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import jwt
import pytest
import socket
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.auth import COOKIE, now, password_hash
from app.config import Settings
from app.database import make_engine, schema_ready, SCHEMA_HEAD
from app.main import create_app
from app.models import AuthSession, User

ORIGIN = {"Origin": "http://127.0.0.1:5173", "X-CSRF-Protection": "1"}
# Synthetic test-only credentials, not an application/admin default.
REG = {"email": "test@example.com", "username": "test_user", "password": "Synthetic-test-password-123"}


def migrate(engine):
    config = Config(str(Path(__file__).resolve().parents[1] / "backend" / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


@pytest.fixture(scope="module")
def postgres():
    settings = Settings()
    if settings.test_db_password is None or settings.jwt_secret is None:
        pytest.fail("Real PostgreSQL private configuration required. Run backend/manage.py configure.")
    if (settings.test_db_name != "gov_policy_test" or settings.test_db_user != "gov_test"
            or settings.db_name == settings.test_db_name or settings.db_user == settings.test_db_user):
        pytest.fail("Test reset requires the dedicated gov_policy_test/gov_test configuration")
    engine = make_engine(settings, test=True)
    with engine.begin() as connection:
        assert connection.scalar(text("SELECT current_database()")) == "gov_policy_test"
        assert connection.scalar(text("SELECT current_user")) == "gov_test"
        assert not connection.scalar(text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user"))
        allowed = {"saved_answers", "users", "auth_sessions", "auth_throttles", "alembic_version", "schemes", "documents", "document_versions", "version_relationships", "extracted_pages", "chunks", "ingestion_jobs", "eligibility_reviews", "index_generations", "index_passages", "index_state", "answer_runs", "answer_worker", "answer_claims", "claim_citations", "extraction_revisions", "extraction_pages", "extraction_reviews", "extraction_state"}
        assert set(inspect(connection).get_table_names()) <= allowed, "Refusing to reset unexpected test tables"
        # Only this explicitly dedicated disposable database may be reset.
        for table in ["saved_answers", "extraction_state", "extraction_reviews", "extraction_pages", "extraction_revisions", "claim_citations", "answer_claims", "answer_worker", "answer_runs", "index_state", "index_passages", "index_generations", "eligibility_reviews", "chunks", "version_relationships", "ingestion_jobs", "extracted_pages", "document_versions", "documents", "schemes", "auth_throttles", "auth_sessions", "users", "alembic_version"]:
            connection.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
        connection.execute(text("DROP FUNCTION IF EXISTS protect_document_version() CASCADE"))
        connection.execute(text("DROP FUNCTION IF EXISTS protect_eligibility_review() CASCADE"))
        connection.execute(text("DROP FUNCTION IF EXISTS protect_extraction_artifact() CASCADE"))
    assert not schema_ready(engine)
    migrate(engine)  # Real migration from empty database.
    migrate(engine)  # Repeated upgrade must be idempotent.
    assert schema_ready(engine)
    assert set(inspect(engine).get_table_names()) == allowed
    yield settings, engine
    engine.dispose()


@pytest.fixture
def api(postgres):
    settings, engine = postgres
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE answer_runs, answer_worker, index_state, index_passages, index_generations, eligibility_reviews, auth_throttles, auth_sessions, chunks, version_relationships, ingestion_jobs, extracted_pages, document_versions, documents, schemes, users CASCADE"))
    app = create_app(settings)
    if app.state.engine:
        app.state.engine.dispose()
    app.state.engine = engine
    app.state.sessions = sessionmaker(engine, expire_on_commit=False)
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        yield client, settings, engine


def signup_login(client):
    assert client.post("/auth/register", headers=ORIGIN, json=REG).status_code == 201
    result = client.post("/auth/login", headers=ORIGIN, json={"email": REG["email"], "password": REG["password"]})
    assert result.status_code == 200
    return result.json(), client.cookies.get(COOKIE)


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_registration_normalization_privilege_and_hash(api):
    client, _, engine = api
    escalated = client.post("/auth/register", headers=ORIGIN, json={**REG, "role": "admin"})
    assert escalated.status_code == 422
    result = client.post("/auth/register", headers=ORIGIN, json={**REG, "email": " TEST@Example.com ", "username": " Test_User "})
    assert result.status_code == 201
    body = result.json()
    assert body["email"] == REG["email"] and body["username"] == REG["username"]
    assert body["role"] == "user" and "password_hash" not in body and REG["password"] not in result.text
    assert client.post("/auth/register", headers=ORIGIN, json=REG).status_code == 409
    assert client.post("/auth/register", headers=ORIGIN, json={**REG, "email": "other@example.com"}).status_code == 409
    assert client.post("/auth/register", headers=ORIGIN, json={**REG, "password": "x" * 129}).status_code == 422
    with Session(engine) as db:
        user = db.scalar(select(User))
        assert user.password_hash.startswith("$argon2id$")
        assert password_hash.verify(REG["password"], user.password_hash)
        assert user.created_at.tzinfo is not None


def test_login_me_profile_and_admin_authorization(api):
    client, _, engine = api
    assert client.get("/auth/admin/access").status_code == 401
    assert client.post("/auth/login", headers=ORIGIN, json={"email": REG["email"], "password": "wrong"}).status_code == 401
    result, _ = signup_login(client)
    headers = auth_header(result["access_token"])
    assert client.get("/auth/me", headers=headers).json()["username"] == REG["username"]
    assert client.patch("/auth/me", headers={**headers, **ORIGIN}, json={"preferred_language": "hi"}).json()["preferred_language"] == "hi"
    assert client.patch("/auth/me", headers={**headers, **ORIGIN}, json={"role": "admin"}).status_code == 422
    assert client.get("/auth/admin/access", headers=headers).status_code == 403
    with Session(engine) as db:
        user = db.scalar(select(User)); user.role = "admin"; db.commit()
    assert client.get("/auth/admin/access", headers=headers).json()["authorized"] is True
    with Session(engine) as db:
        user = db.scalar(select(User)); user.role = "user"; db.commit()
    assert client.get("/auth/admin/access", headers=headers).status_code == 403


@pytest.mark.parametrize("kind", ["expired", "tampered", "issuer", "audience", "algorithm", "missing"])
def test_invalid_access_tokens(api, kind):
    client, settings, _ = api
    result, _ = signup_login(client)
    key = settings.jwt_secret.get_secret_value()
    claims = jwt.decode(result["access_token"], key, algorithms=["HS256"], audience=settings.jwt_audience, issuer=settings.jwt_issuer)
    if kind == "expired": claims["exp"] = int((now() - timedelta(minutes=1)).timestamp())
    if kind == "issuer": claims["iss"] = "wrong"
    if kind == "audience": claims["aud"] = "wrong"
    if kind == "missing": del claims["exp"]
    token = jwt.encode(claims, "wrong-secret-that-is-long-enough-1234" if kind == "tampered" else key,
                       algorithm="HS512" if kind == "algorithm" else "HS256")
    assert client.get("/auth/me", headers=auth_header(token)).status_code == 401


def test_rotation_reuse_and_logout(api):
    client, _, engine = api
    result, old = signup_login(client)
    refreshed = client.post("/auth/refresh", headers=ORIGIN)
    assert refreshed.status_code == 200
    assert client.cookies.get(COOKIE) != old
    with Session(engine) as db:
        session = db.scalar(select(AuthSession))
        assert old not in session.refresh_hash and len(session.used_hashes) == 1
    new_cookie = client.cookies.get(COOKIE)
    client.cookies.clear()
    replay = client.post("/auth/refresh", headers={**ORIGIN, "Cookie": f"{COOKIE}={old}"})
    assert replay.status_code == 401
    assert "Max-Age=0" in replay.headers["set-cookie"]
    assert client.get("/auth/me", headers=auth_header(result["access_token"])).status_code == 401
    client.cookies.clear()
    assert client.post("/auth/refresh", headers={**ORIGIN, "Cookie": f"{COOKIE}={new_cookie}"}).status_code == 401
    logged = client.post("/auth/login", headers=ORIGIN, json={"email": REG["email"], "password": REG["password"]})
    assert logged.status_code == 200
    assert client.post("/auth/logout", headers=ORIGIN).status_code == 204
    assert client.get("/auth/me", headers=auth_header(logged.json()["access_token"])).status_code == 401


def test_concurrent_refresh_is_atomic(api):
    client, _, _ = api
    _, old = signup_login(client)
    def rotate():
        with TestClient(client.app, base_url="http://127.0.0.1:8000") as other:
            return other.post("/auth/refresh", headers={**ORIGIN, "Cookie": f"{COOKIE}={old}"}).status_code
    with ThreadPoolExecutor(max_workers=2) as workers:
        assert sorted(workers.map(lambda _: rotate(), range(2))) == [200, 401]


def test_logout_revokes_access_session_even_without_cookie(api):
    client, _, _ = api
    result, _ = signup_login(client)
    client.cookies.clear()
    headers = {**ORIGIN, **auth_header(result["access_token"])}
    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_disabled_expired_and_revoked_sessions(api):
    client, _, engine = api
    result, _ = signup_login(client)
    with Session(engine) as db:
        user = db.scalar(select(User)); user.active = False; db.commit()
    assert client.get("/auth/me", headers=auth_header(result["access_token"])).status_code == 401
    assert client.post("/auth/refresh", headers=ORIGIN).status_code == 401
    with Session(engine) as db:
        user = db.scalar(select(User)); user.active = True; db.commit()
    logged = client.post("/auth/login", headers=ORIGIN, json={"email": REG["email"], "password": REG["password"]})
    with Session(engine) as db:
        session = db.scalar(select(AuthSession).where(AuthSession.revoked_at.is_(None)))
        # Keep DB expiry constraint valid while making it expired.
        session.created_at = now() - timedelta(days=2); session.expires_at = now() - timedelta(days=1); db.commit()
    assert client.get("/auth/me", headers=auth_header(logged.json()["access_token"])).status_code == 401
    assert client.post("/auth/refresh", headers=ORIGIN).status_code == 401


def test_origin_csrf_and_cookie_flags(api):
    client, _, _ = api
    assert client.post("/auth/register", json=REG).status_code == 403
    assert client.post("/auth/register", headers={"Origin": "https://evil.example", "X-CSRF-Protection": "1"}, json=REG).status_code == 403
    assert client.post("/auth/register", headers={"Origin": ORIGIN["Origin"]}, json=REG).status_code == 403
    result, _ = signup_login(client)
    login_result = client.post("/auth/login", headers=ORIGIN, json={"email": REG["email"], "password": REG["password"]})
    cookie = login_result.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/auth" in cookie
    assert client.post("/auth/logout", headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.post("/auth/refresh", headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.get("/auth/me", headers=auth_header(result["access_token"])).status_code == 200


def test_throttle_persists_and_does_not_trust_forwarded_ip(api):
    client, settings, engine = api
    for _ in range(settings.login_limit):
        assert client.post("/auth/login", headers=ORIGIN, json={"email": REG["email"], "password": "wrong"}).status_code == 401
    replacement = create_app(settings)
    replacement.state.engine.dispose()
    replacement.state.engine = engine; replacement.state.sessions = sessionmaker(engine)
    with TestClient(replacement) as restarted:
        result = restarted.post("/auth/login", headers={**ORIGIN, "X-Forwarded-For": "8.8.8.8"}, json={"email": REG["email"], "password": "wrong"})
        assert result.status_code == 429
    with engine.begin() as connection:
        connection.execute(text("UPDATE auth_throttles SET window_start = now() - interval '1 hour'"))
    assert client.post("/auth/login", headers=ORIGIN, json={"email": REG["email"], "password": "wrong"}).status_code == 401


def test_session_survives_app_recreation_and_schema_readiness(api):
    client, settings, engine = api
    result, cookie = signup_login(client)
    assert client.get("/health/ready").status_code == 200
    replacement = create_app(settings)
    replacement.state.engine.dispose()
    replacement.state.engine = engine; replacement.state.sessions = sessionmaker(engine)
    with TestClient(replacement) as restarted:
        assert restarted.get("/auth/me", headers=auth_header(result["access_token"])).status_code == 200
        assert restarted.post("/auth/refresh", headers={**ORIGIN, "Cookie": f"{COOKIE}={cookie}"}).status_code == 200
    with engine.begin() as connection:
        connection.execute(text("UPDATE alembic_version SET version_num='missing'"))
    assert client.get("/health/ready").status_code == 503
    assert client.get("/health/live").status_code == 200
    with engine.begin() as connection:
        connection.execute(text("UPDATE alembic_version SET version_num=:head"), {"head": SCHEMA_HEAD})


def test_configured_but_unreachable_database_readiness(postgres):
    settings, _ = postgres
    # Reserve a local non-listening port so this cannot target a real database/service.
    with socket.socket() as unavailable:
        unavailable.bind(("127.0.0.1", 0))
        port = unavailable.getsockname()[1]
        app = create_app(settings.model_copy(update={"db_port": port}))
        with TestClient(app) as client:
            assert client.get("/health/live").status_code == 200
            response = client.get("/health/ready")
            assert response.status_code == 503
            assert settings.db_password.get_secret_value() not in response.text
        app.state.engine.dispose()
