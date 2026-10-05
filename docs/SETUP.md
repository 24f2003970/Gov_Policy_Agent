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

Expected head: `0003_retrieval`. Upgrade is additive and repeatable; startup does not create tables. Downgrades remove data and are not a setup step.

Create the first administrator only when none exists:

```powershell
.\.venv\Scripts\python.exe backend\manage.py bootstrap-admin
```

The command prompts for identity and hidden password confirmation. Existing installations retain their administrator. Secrets stay in ignored `.env`; never include them in logs, screenshots or public files.

## Prepare the embedding model

Run explicitly once (network download from the pinned official Hugging Face revision):

```powershell
.\.venv\Scripts\python.exe backend\prepare_model.py
```

Expected output includes `intfloat/multilingual-e5-small`, revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`, 384 dimensions and CPU configuration. The lock uses the official PyTorch CPU wheel index. No CUDA stack is required. Model files default to `%LOCALAPPDATA%\GovPolicyAgent\models`; subsequent API/model startup is offline and rejects an absent/mismatched preparation manifest. Downloading another revision requires a deliberate code/spec change and index rebuild.

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

Terminal 4, root:

```powershell
.\.venv\Scripts\python.exe backend\index.py serve
```

This loads one CPU model and owns Chroma under a Windows file lock, then starts a private loopback service on port 8011. Wait for Uvicorn startup (measured runtime load about 16 seconds). Do not start additional index owners or use reload/multiple workers. API startup does not load the model. The internal query endpoint requires a private derived key; use the authenticated API/UI instead.

Use `http://127.0.0.1:5173/` consistently; `localhost` is a different origin. Admin uploads are at `/#admin`; protected retrieval is at `/#search`. Sign in, enter a Hindi/English question and select Search passages. Filters match exact stored scheme/issuer/type; date bounds concern publication dates, with an explicit unknown-date choice. Inspect extracted source text from a result. Only admins can review/upload/rebuild or fetch original PDF/PNG. API docs: `http://127.0.0.1:8000/docs`; readiness: `/health/ready`. Ready checks DB/schema/auth, not index-service availability. Stop terminals with Ctrl+C.

## Storage and corpus operations

Durable originals default to `%LOCALAPPDATA%\GovPolicyAgent\data`, outside OneDrive. `GOV_DATA_DIR` can override this in private `.env`; model/vector directories are siblings of that data directory. Back up the database and originals together; Chroma is derived and rebuildable. To relocate, stop all services, copy storage, update the setting and verify original checksums. Paths must remain private and outside frontend assets.

Optional root commands:

```powershell
.\.venv\Scripts\python.exe backend\worker.py --once
.\.venv\Scripts\python.exe backend\worker.py --reconcile
.\.venv\Scripts\python.exe backend\corpus.py --download
.\.venv\Scripts\python.exe backend\corpus.py --import
.\.venv\Scripts\python.exe backend\index.py rebuild
.\.venv\Scripts\python.exe backend\index.py status
```

Worker reconcile removes only generated unreferenced originals older than 24 hours and temporary files older than one hour. Corpus download verifies [manifest](corpus_manifest.json) hashes; changed sources require review. Import requires an existing active first admin, reuses versions on repeat and records the manifest's explicit audited review for the PIB factsheet only. Inspect extraction before rebuild. The existing three sources remain restricted. Source terms/scope are in [SOURCES.md](SOURCES.md).

Rebuild prints a queued generation UUID; the running index service processes it. Repeated pending requests reuse the job. Status prints source exclusion reasons and durable progress; `ready` means a completed SQL generation, not a live-service probe. Failed jobs below three attempts can retry through the admin API; exhausted jobs require a new rebuild.

Stop Terminal 4 before these maintenance commands (each requires exclusive vector ownership):

```powershell
.\.venv\Scripts\python.exe backend\index.py once
.\.venv\Scripts\python.exe backend\index.py reconcile
.\.venv\Scripts\python.exe backend\evaluate_retrieval.py
```

`once` claims one queued/expired job. Index reconcile removes orphan vector IDs; missing SQL-referenced vectors clear the active pointer and mark failure, requiring retry/rebuild. Old generation SQL provenance is retained; automatic old-collection garbage collection is deferred. Evaluation checks the eligible real source and writes ignored `runtime/retrieval-results.json`; it never substitutes fixtures. Restart `index.py serve` afterwards.

## Checks

Root commands; prepare the model first. Tests reset only the dedicated test database and use temporary vector/storage collections:

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
| Search 503/busy | Start the prepared single-owner service; retry after a batch finishes |
| Model missing/mismatched | Run explicit preparation; preserve the pinned spec |
| Index owner lock | Stop the other index service before offline maintenance |
| No results | Check eligibility, exact filters, dates and heuristic cutoff; no answer is asserted |
| Review changed after indexing | Rebuild; new review must be included in the active snapshot |
| Query 422 | Shorten to 2–2000 characters and at most 512 actual prefixed tokens |
