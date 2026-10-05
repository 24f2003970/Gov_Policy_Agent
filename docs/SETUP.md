# Windows setup

All root commands run from the repository directory in PowerShell. Prerequisites: Python 3.12, Node 22.12+ with npm, Git and PostgreSQL 18 with Server/Command Line Tools. Tested versions are in [verification](VERIFICATION.md). Use [official PostgreSQL Windows installation](https://www.postgresql.org/download/windows/); Stack Builder packages are unnecessary. Keep PostgreSQL on loopback port 5432.

## Dependencies

For a fresh clone only, create the environment; preserve an existing `.venv` and private `.env`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock
npm.cmd --prefix frontend ci
```

The existing development environment uses bundled Python 3.12.14; an independent installation is needed on another machine. Activation is unnecessary. `npm.cmd` avoids PowerShell npm.ps1 execution-policy issues.

## Database and administrator

Fresh installations only:

```powershell
.\.venv\Scripts\python.exe backend\manage.py configure
```

Enter the PostgreSQL administrator password at the hidden prompt. This creates private `.env` credentials for `gov_app/gov_policy` and disposable `gov_test/gov_policy_test`, verifies ownership and uses non-superuser roles. If it requests a service restart after setting loopback listening, run `Restart-Service postgresql-x64-18` in administrator PowerShell, then rerun configure. Do not provision again on an already configured installation or overwrite `.env` with example values.

Apply migrations for both fresh and existing application installations:

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini current
```

Expected head: `0002_documents`. Upgrade is repeatable; startup does not create tables. Downgrades remove data and are not a setup step.

Create the first administrator only when none exists:

```powershell
.\.venv\Scripts\python.exe backend\manage.py bootstrap-admin
```

The command prompts for identity and hidden password confirmation. Existing installations retain their administrator. Secrets stay in ignored `.env`; never include them in logs, screenshots or public files.

## Start

Terminal 1, root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Terminal 2, root:

```powershell
npm.cmd --prefix frontend run dev
```

Terminal 3, root:

```powershell
.\.venv\Scripts\python.exe backend\worker.py
```

Use `http://127.0.0.1:5173/` consistently; `localhost` is a different origin. Admin uploads are at `/#admin`. API docs: `http://127.0.0.1:8000/docs`; readiness: `/health/ready`. Ready requires configured authentication and the current PostgreSQL schema. Worker output begins `Worker running; one job at a time. Ctrl+C to stop.` Stop terminals with Ctrl+C.

## Storage and corpus operations

Durable originals default to `%LOCALAPPDATA%\GovPolicyAgent\data`, outside OneDrive. `GOV_DATA_DIR` can override this in private `.env`. Back up the database and data directory together. To relocate, stop API/worker, copy the complete storage directory, update the setting and verify original checksums after restart. Paths must remain private and outside frontend assets.

Optional root commands:

```powershell
.\.venv\Scripts\python.exe backend\worker.py --once
.\.venv\Scripts\python.exe backend\worker.py --reconcile
.\.venv\Scripts\python.exe backend\corpus.py --download
.\.venv\Scripts\python.exe backend\corpus.py --import
```

Reconcile removes only generated unreferenced originals older than 24 hours and temporary files older than one hour. Corpus download verifies [manifest](corpus_manifest.json) hashes; changed sources require review. Import requires an existing active first admin and reuses versions on repeat. Source rights restrictions remain in [SOURCES.md](SOURCES.md).

## Checks

Root commands; tests reset only the dedicated test database and use temporary storage:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run build
```

If old Windows pytest temporary directories are inaccessible, supply `--basetemp=runtime/pytest-check-NEW` with a new unused directory name. Database tests fail when private test prerequisites are missing; they do not substitute SQLite.

| Symptom | Check |
| --- | --- |
| Ready returns 503 | PostgreSQL service, private settings and `upgrade head` |
| Queued job | Worker running, schema current, document not archived |
| Partial/needs_ocr | Inspect flagged pages; OCR is deferred |
| Upload 409 | Same bytes with conflicting metadata; inspect the existing version |
| Upload 413/422 | Actual stream size or parser/file validation limits |
| Inspection 401/403 | Session, admin role and approved 127.0.0.1 origin |
| Missing/changed original | Restore matching storage/database backup |
