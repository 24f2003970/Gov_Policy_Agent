## Multilingual Government Policy Assistant

**GOV-CS-028** · B.Tech project · Part 3 reliable document ingestion

A local application being developed to answer English, Hindi and practical Hinglish policy questions from verified official evidence. The final system will support grounded RAG, claim-level citations and an experimental evidence-quality index. These capabilities are **planned**, not implemented or measured yet.

Parts 1/2 are preserved: foundation, PostgreSQL accounts, rotating sessions and server-enforced roles. Part 3 adds admin PDF/UTF-8 TXT uploads, immutable source versions, protected originals/page previews, provenance, exact extraction spans, provisional chunks and a separate durable worker. Current local demo contains 3 official-origin PDFs across 3 schemes (164 pages); originals stay private/ignored, all local-reference-only. No embeddings, policy answers, RAG or AI models yet. Executed checks are in [PROGRESS.md](PROGRESS.md).

## Start on Windows PowerShell

From the repository root, with existing private PostgreSQL configuration; apply current migration per [docs/SETUP_PART3.md](docs/SETUP_PART3.md):

```powershell
# Terminal 1
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --no-proxy-headers
```

```powershell
# Terminal 2
Set-Location frontend
npm.cmd run dev
```

```powershell
# Terminal 3, repository root; durable ingestion runs separately
.\.venv\Scripts\python.exe backend\worker.py
```

Open http://127.0.0.1:5173. Foundation should show **Connected · Foundation ready** with current DB/schema. Existing admin login then /#admin opens uploads/list/inspection. Status polling reads persisted jobs; worker must run to process queued work. API docs: http://127.0.0.1:8000/docs. Stop each terminal with Ctrl+C.

```powershell
# Run from the repository root
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
Set-Location frontend
npm.cmd run build
```

## Layout

```text
backend/app/     FastAPI, configuration, database and authentication
backend/migrations/ explicit Alembic schema revisions
frontend/src/    foundation, health/auth clients and document admin UI
docs/           setup, architecture, verification and beginner explanations
scripts/        PowerShell startup and verification helpers
tests/          foundation/security and real PostgreSQL auth/ingestion tests
```

## Project records

- [Current PostgreSQL/auth setup](docs/SETUP_PART2.md) and [Part 1 environment record](docs/SETUP.md)
- [Current ingestion/worker/corpus setup](docs/SETUP_PART3.md) and [reproducible corpus manifest](docs/corpus_manifest.json)
- [Architecture and planned relational design](docs/ARCHITECTURE.md)
- [Beginner code walkthrough and viva](docs/WALKTHROUGH.md)
- [Roadmap](PROJECT_PLAN.md), [progress](PROGRESS.md), [decisions](DECISIONS.md)
- [Proposal requirement mapping](REQUIREMENTS_MATRIX.md)
- [Executed verification](docs/VERIFICATION.md)

## Learning Guide

Simple conversational Hinglish, actual source links, exact commands, limitations and viva practice:

- [Part 1: working foundation](docs/learning/PART_01_EXPLAINED.md)
- [Part 2: accounts, PostgreSQL and permissions](docs/learning/PART_02_EXPLAINED.md)
- [Part 3: reliable document upload and ingestion](docs/learning/PART_03_EXPLAINED.md)

Every future numbered part must add/update its own docs/learning/PART_XX_EXPLAINED.md in the same verified phase commit. Historical guides describe delivered behavior and explicitly distinguish current changes.

The local 34-page proposal was read as a requirements reference. It is ignored by Git and must never become chatbot evidence. Uploaded documents, secrets, local data and model weights are also ignored. No accuracy, novelty, publication or production-scale claims have been established.
