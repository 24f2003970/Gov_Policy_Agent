# Part 2 — PostgreSQL and authentication (Windows PowerShell)

Work in `C:\Users\thiss\OneDrive\Documents\ChatGPT\Gov_Policy_Agent`. Keep the existing bundled-Python .venv. No Docker or AI model is required.

## Native installation and private setup

Target PostgreSQL **18**, current supported minor **18.6** (checked 2026-10-05). The trusted winget package is `PostgreSQL.PostgreSQL.18` version `18.6-5`; official installer:

https://get.enterprisedb.com/postgresql/postgresql-18.6-5-windows-x64.exe

Published winget SHA256: `227e2bc08091b4c2b8338c7d61b11d057f895711480b006f90bfcfcd2410a58a`.

This is the EDB installer linked by [PostgreSQL's official Windows page](https://www.postgresql.org/download/windows/). PostgreSQL 18 is supported through 2030 per [the official version policy](https://www.postgresql.org/support/versioning/). An installed binary/version/service must still be verified; downloading an installer is not installation completion.

User actions in the installer: approve UAC if shown; keep `C:\Program Files\PostgreSQL\18`; select Server and Command Line Tools (pgAdmin optional); choose the postgres administrator password privately; default data folder/port 5432 and locale are suitable; skip Stack Builder. Do not put the password in chat or arguments. No default administrator password is supplied by this project.

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' --version
Get-Service postgresql-x64-18
& 'C:\Program Files\PostgreSQL\18\bin\pg_isready.exe' -h 127.0.0.1 -p 5432
```

Then in your own interactive PowerShell terminal:

```powershell
Set-Location 'C:\Users\thiss\OneDrive\Documents\ChatGPT\Gov_Policy_Agent'
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock
.\.venv\Scripts\python.exe backend\manage.py configure
```

Enter the postgres password in hidden input. The script generates unique random app/test role passwords and a signing secret, writes them directly to ignored .env, and verifies role connections. Existing unrelated .env settings and an existing JWT secret are preserved. It refuses to overwrite custom database names/users or take over databases with another owner. Credentials are saved privately before role creation, so interruptions do not lose newly generated passwords. Errors are sanitized.

If the server is listening on all interfaces, configure writes `listen_addresses='localhost'` and stops before role provisioning. Run the printed command in **administrator PowerShell**, then rerun configure:

```powershell
Restart-Service postgresql-x64-18
```

The normal app uses `gov_app` and database `gov_policy`. Tests use `gov_test` and disposable `gov_policy_test`. Neither role has SUPERUSER/CREATEDB/CREATEROLE/REPLICATION. Each owns only its dedicated database so explicit migrations can manage its tables. PUBLIC database access/schema creation are revoked. Never use postgres for API requests. No resets are performed on the application database.

Secrets live in `.env` using separate fields, not a hand-built DSN: `GOV_DB_PASSWORD`, `GOV_TEST_DB_PASSWORD`, `GOV_JWT_SECRET`. SQLAlchemy URL.create handles password punctuation such as `@`, `%` and `:` safely. A manually written URL would need percent encoding; this implementation avoids that. Do not print/cat `.env`, SQL exception details or connection URLs when asking for support. Local ignored files remain sensitive—keep OneDrive sharing/private backups under your control.

## Explicit migrations and first administrator

```powershell
# Root directory; real PostgreSQL must be available
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini current
# Safe to repeat upgrade head; no automatic startup table creation
.\.venv\Scripts\python.exe backend\manage.py bootstrap-admin
```

Bootstrap asks email, username and hidden password twice. It only creates the first admin, serializes concurrent bootstrap commands, uses the same 12–128 character validation, and refuses duplicate data. Public registration always creates user accounts; submitted role fields are rejected. Do not run downgrade on the application DB casually; it deletes authentication data.

## Start and browser URLs

```powershell
# Terminal 1, repository root; disable proxy headers so IP throttling cannot be spoofed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --no-proxy-headers
```

```powershell
# Terminal 2
Set-Location 'C:\Users\thiss\OneDrive\Documents\ChatGPT\Gov_Policy_Agent\frontend'
npm.cmd ci
npm.cmd run dev
```

Use **127.0.0.1 consistently**, not localhost. Origin http://127.0.0.1:5173 is approved; API base http://127.0.0.1:8000. These different ports are same-site for cookies but distinct origins for CORS.

- `/` or `/#home`: preserved foundation screen and phase-2 readiness.
- `/#register`, `/#login`: actual forms/API requests.
- `/#account`: protected profile, preferred-language update and logout.
- `/#admin`: actual backend admin authorization result. Navigation hidden for normal users; typing the URL cannot bypass server role checks.
- API `/docs`, `/openapi.json`, `/health/live`, `/health/ready` remain available.

Readiness needs configured JWT secret and PostgreSQL with migration `0001_auth` plus required columns. Missing DB/schema returns sanitized HTTP 503. Liveness does not contact DB. Checks use two-second connect, statement, lock and pool timeouts; pool pre-ping detects stale connections. Chroma/Ollama remain not required. The UI readiness indicator is a snapshot, not continuous monitoring.

## Authentication and browser safety design

Synchronous SQLAlchemy/psycopg and Argon2 operations run in FastAPI worker threads (sync routes/dependencies). Access JWT is HS256 only, 10-minute default, with validated signature/exp/iat/nbf/issuer/audience/sub/session ID/token-use. Backend checks the persisted session and current user's active flag/role for every protected request. Logout/disable therefore invalidates access even before JWT expiry.

Refresh tokens are high-entropy opaque `session-id.random` values, stored only as SHA256 digests. Cookie is host-only, HttpOnly, SameSite=Strict, path=/auth; no token in localStorage/sessionStorage. Production configuration requires Secure cookies and explicit HTTPS CORS origins. HTTP/non-Secure cookies are limited to documented 127.0.0.1 development/test use. Final public deployment/TLS remains Part 12.

Every auth mutation requires an approved exact Origin **and** X-CSRF-Protection:1; preflight CORS permits that custom header only from approved origins. SameSite and cookie paths supplement these controls. Non-browser tools must deliberately supply these headers too. Browser fetch includes credentials. PATCH profile also needs the access bearer token.

Refresh uses SELECT FOR UPDATE to consume/rotate in a single transaction. Known old-token reuse revokes the whole session (fail closed). An arbitrary invalid hash cannot revoke someone else's session just by guessing its UUID. A session retains at most 256 consumed digests and then requires a new login; absolute expiry is seven days by default, not extended by rotation.

Frontend shares one in-flight refresh promise per tab and Web Locks serialize refresh/login/logout across same-origin tabs. A protected request may refresh once and retry once; no refresh loop. BroadcastChannel clears other tabs' memory on logout. On browsers without Web Locks, simultaneous cross-tab rotation may trigger reuse revocation and require re-login; no unsafe grace token is issued. XSS can still perform actions in an authenticated page: HttpOnly helps protect refresh-token reading, not all XSS risk. CSP and broader security review remain Part 11.

Login throttle records persist in PostgreSQL, keyed by HMAC-hashed normalized account/IP. Default five account login attempts per 15-minute fixed window; IP limit is 10× that, also protecting signup. All attempts count, including success; no permanent lockout. Expired records are pruned and table is capped at 10,000 keys. PostgreSQL advisory/row locks keep counts consistent. Do not enable Uvicorn proxy headers in this local setup or trust client-supplied X-Forwarded-For.

## Real PostgreSQL verification

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
Set-Location frontend
npm.cmd run typecheck
npm.cmd run build
```

Tests deliberately fail if private PostgreSQL configuration is unavailable. They do not substitute SQLite or mock successful auth. The fixture requires the exact dedicated `gov_policy_test`/`gov_test` pair, refuses unexpected tables/superuser access, and only resets that disposable database. It migrates from empty, upgrades twice, checks actual transactions, normalization, hashing, token validation, roles, rotation/reuse/concurrency/revocation, CSRF, durable throttling and app recreation. Tests never reset `gov_policy`.

Browser checks must additionally verify registration, login, reload restoration, profile update, logout, normal-user admin denial and actual admin login. App recreation tests do not by themselves prove an actual process restart; record process/browser checks separately in VERIFICATION.md.

## References for chosen APIs

Consulted official [SQLAlchemy PostgreSQL/psycopg](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#psycopg), [psycopg installation](https://www.psycopg.org/psycopg3/docs/basic/install.html), [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html), [pwdlib](https://frankie567.github.io/pwdlib/reference/pwdlib/) and [PyJWT usage](https://pyjwt.readthedocs.io/en/latest/usage.html). Direct dependencies and full transitive lock remain backend/requirements.in + requirements.lock; frontend package-lock is unchanged by auth UI work.
