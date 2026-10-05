# Part 3 - reliable local document ingestion

## Existing installation

Work from `C:\Users\thiss\OneDrive\Documents\ChatGPT\Gov_Policy_Agent`. Keep existing `.venv`, ignored `.env`, PostgreSQL roles/databases and first admin. Do not rerun provisioning, recreate admin, or reset application data.

```powershell
Set-Location 'C:\Users\thiss\OneDrive\Documents\ChatGPT\Gov_Policy_Agent'
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini current
```

Expected head: `0002_documents`. Explicit migration adds seven phase-specific tables and an immutability trigger; auth tables/data are retained. Repeated upgrade is safe. Do not downgrade the application database to experiment: it deletes document metadata/extraction.

## Three terminals

Terminal 1, repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Terminal 2, root then frontend:

```powershell
Set-Location frontend
npm.cmd run dev
```

Terminal 3, repository root:

```powershell
.\.venv\Scripts\python.exe backend\worker.py
```

Expected: `Worker running; one job at a time. Ctrl+C to stop.` API remains usable when worker stops; jobs persist. Worker reconnects after DB outages. Recovered expired jobs have at most three total attempts.

One-shot processing and explicit orphan cleanup, root:

```powershell
.\.venv\Scripts\python.exe backend\worker.py --once
.\.venv\Scripts\python.exe backend\worker.py --reconcile
```

Reconcile removes only generated unreferenced originals older than 24 hours and temporary artifacts older than one hour. It refuses symlinks/unknown names and preserves referenced originals. Storage must remain under exclusive application control; manual file deletion/copying during uploads is unsupported.

## Private storage and moving it

Actual default on this laptop: `C:\Users\thiss\AppData\Local\GovPolicyAgent\data`, outside OneDrive. `originals` contains generated UUID filenames; `temporary` contains upload/parser artifacts. No public static mount exists. API never returns raw paths. The download cache is ignored `runtime/corpus` in this checkout; it is not the durable originals directory.

Optional ignored `.env` setting (path only; preserve existing secrets):

```dotenv
GOV_DATA_DIR=C:/Users/thiss/AppData/Local/GovPolicyAgent/data
```

To move storage: stop API and worker, back up the database **and** data directory together, copy the complete originals/temporary directories to the new private directory, update only GOV_DATA_DIR, restart, verify protected original checksums. DB stores generated relative keys, not absolute paths. Changing the setting without copying files causes missing-original failures. Do not point it at frontend assets or share the directory publicly.

## Admin UI

Use `http://127.0.0.1:5173/#login`, privately enter existing admin credentials, then Admin. Normal users receive backend 403 even if they type the route directly.

1. Choose PDF or UTF-8 TXT, maximum **50 MiB = 52,428,800 bytes**.
2. Enter title, issuer, optional scheme, document type, claimed source URL and language. Leave unknown publication/effective dates blank. Choose truthful reuse rights.
3. Upload and queue. It starts unverified; merely looking official does not verify it.
4. Run the separate worker. Selected job polls every three seconds, no concurrent polls, maximum 120 polls per state; leaving the page clears polling. Manual Refresh status/list remains available.
5. Select document/version, inspect original physical PDF page numbers or TXT section spans. Text windows are 20,000 characters with next/previous controls, not silent truncation.
6. Load original preview renders the selected PDF page as a bounded PNG from original bytes. The authenticated PDF/TXT download uses the unchanged original; no embedded document HTML/JavaScript is executed.
7. Record a manual provenance note only after checking source/title/issuer/rights. Archived documents remain downloadable to admin but are ineligible for future retrieval and skipped by queued worker claiming. Unarchive reverses archive status.

Retry accepts only failed jobs below three attempts. Completed jobs cannot be casually reprocessed; needs_ocr/partial await Part 7. Archive is used instead of hard deletion. Adding a version requires new bytes plus selected document ID and the same title/issuer/type/scheme. There is no automatic supersession based on date.

## API conventions

All document endpoints are under `/admin/documents`; require current admin JWT. Mutations also require exact approved Origin and X-CSRF-Protection:1. Upload uses raw binary request body, filename query, and URI-encoded JSON in **X-Document-Metadata** header; metadata stays out of access-log URLs. Browser native Blob fetch avoids multipart pre-auth buffering. `/docs` documents fields/endpoints.

GET list/detail/status/pages/page-text/chunks/relationships/original/preview are protected. POST upload/retry/relationship and PATCH archive/provenance are controlled mutations. Version snapshot/original identifiers have a PostgreSQL immutability trigger; verification decisions are one-time in this phase. Correcting decisions/audited deletion is a later workflow.

## Validation, limits and provenance

Size counted while streaming; Content-Length/MIME labels are not trusted. Filenames cannot contain paths; generated storage keys prevent traversal/overwrite. Upload has a 60-second reading deadline. Parser children have a 30-second default wall-clock deadline, maximum 500 PDF pages and 2,000,000 extracted characters. TXT must decode as UTF-8, cannot contain binary control data/PDF content, and cannot be empty. Malformed/repaired/encrypted PDFs are rejected. Parser processes omit GOV_* environment values and suppress stdout/stderr.

PDF extraction is exact `get_text('text', sort=False)` output, not visually perfect reading order. Low-text (<30 stripped characters) pages are conservatively needs_ocr, including potentially blank/decorative pages. Mixed documents retain digital text but remain partial. Tables/layout and encoding artifacts need human review. Regex paragraph/heading detection is heuristic; absent clause identifiers remain null.

Chunk profile `unicode-char-v1:1200:120` is provisional: max 1,200 Unicode characters, 120 overlap, prefer a newline boundary after 600 characters. Half-open offsets `[start,end)` refer to exact extracted page text; TXT also has source_start and no invented PDF page number. Oversized paragraphs/clauses get continued-clause metadata. Part 4 can regenerate derived chunks from stored text using its chosen tokenizer; no embedding model downloaded.

Global corpus SHA256 deduplication: same bytes/same metadata return existing version/job. Same bytes/conflicting metadata or target document yield 409. Distinct bytes create a distinct immutable version. Checksums prove byte identity, not official authenticity or legal correctness. Retrieval eligibility is only a **future gate**: completed extraction, verified provenance, permission_recorded reuse status and active document. No retrieval exists yet.

## Worker reliability

Job claiming uses PostgreSQL row locks + SKIP LOCKED. Claim gets a random lease-owner token, 45-second default lease and increments attempt count. Heartbeats while child runs extend lease and record page progress (maximum 95% before result commit). Child results remain temporary until one transaction writes all pages/chunks and terminal state. Expired leases recover on restart; ownership fencing stops old workers publishing after a new claim. Results are idempotently replaced within a transaction, not partially exposed.

One parser per worker; one worker recommended on this 16 GB laptop. Additional workers have transactional claim protection but are not resource-benchmarked. File/page/text/time/output limits bound normal workload. Child is **not an OS security sandbox and has no hard OS memory quota**; malicious native parser exploits/resource bombs remain a security-review risk. Virus scanner did not run and is unavailable. Do not treat upload acceptance as malware clearance. Concurrent API requests also lack a global memory/concurrency admission budget.

## Reproducible real corpus

[corpus_manifest.json](corpus_manifest.json) records three sources: PM-KISAN (12 pages), PMJDY (40), PMAY-U 2.0 (112), retrieved 2026-10-05, checksums, titles, official origin observations, rights limits and unknown dates. Real original PDFs/covers inspected; historical documents are not current entitlement advice. Exact day of publication/effectiveness is not invented.

```powershell
# Root; downloads must still match inspected manifest checksums
.\.venv\Scripts\python.exe backend\corpus.py --download
# Explicit local import uses existing active first admin; never creates an account
.\.venv\Scripts\python.exe backend\corpus.py --import
```

Import reuses upload validation/dedup logic and manifest provenance note. Repeating import returns existing versions. Worker processes queued versions separately. Downloads follow verified TLS, limited same-host redirects, size/time limits and expected hash; changed/blocked files fail instead of being silently accepted.

All three are local-reference-only. [PM-KISAN copyright policy](https://www.pmkisan.gov.in/CopyrightPolicy.aspx) and [PMAY copyright policy](https://pmay-urban.gov.in/copyright) require reproduction permission; none obtained. PMJDY official accessibility page lists a copyright policy but its text was unavailable. No blanket reuse license claimed; no source PDFs/extracted corpus text in Git. Source-origin verification is separate from permission to publish/reuse. Proposal PDF and synthetic fixtures are not real corpus evidence.

## Tests and troubleshooting

```powershell
# Root; real dedicated test DB required, private storage is temporary/isolated
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pip check
Set-Location frontend
npm.cmd run typecheck
npm.cmd run build
```

Tests refuse unexpected test tables/roles and never reset application DB. See [VERIFICATION.md](VERIFICATION.md) for final executed counts and browser evidence.

| Symptom | Fix |
| --- | --- |
| Queued indefinitely | Start worker; inspect migration/DB readiness; unarchive if necessary |
| Partial/needs_ocr | Inspect flagged original pages; OCR intentionally deferred, do not call it fully processed |
| Duplicate metadata 409 | Inspect existing version; repeat exact metadata or upload genuinely new bytes as a new version |
| Parser/time/text/page rejection | Check digital/unencrypted valid format and documented limits; split sources deliberately, not silently truncate |
| Worker killed | Restart; wait for lease expiry; max three attempts; inspect sanitized error code |
| Original missing/changed | Restore matching backup; don't overwrite original with different bytes |
| Refresh/inspection error | Retry Refresh status or select document again; re-login if session expired |
| Corpus command failure | Check official source availability/hash/local cache/schema; changed source requires manual manifest review |
| UI 401/403 | Login with existing admin; use 127.0.0.1 hostname and approved origin |

## Official API references

Consulted [PyMuPDF page extraction](https://pymupdf.readthedocs.io/en/latest/page.html), [document validation](https://pymupdf.readthedocs.io/en/latest/document.html), [installation](https://pymupdf.readthedocs.io/en/latest/installation.html), [licensing](https://pymupdf.io/licensing), [PostgreSQL 18 SELECT/SKIP LOCKED](https://www.postgresql.org/docs/18/sql-select.html). PyMuPDF is AGPL/commercial dual licensed; free academic/open-source use must respect AGPL obligations. Proprietary redistribution needs a separate licensing review. Raw-stream design avoids introducing python-multipart because no multipart endpoint is used.
