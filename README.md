# Multilingual Government Policy Assistant

GOV-CS-028 is a B.Tech student project for exploring document-grounded government policy question answering in English, Hindi and Hinglish. The current application provides authentication, document ingestion, multilingual passage retrieval and local English/Hindi answers from reviewed historical sources.

## Implemented features

- Registration, login, rotating sessions, language preference and server-enforced user/admin roles.
- Admin PDF/UTF-8 TXT upload, immutable document versions, checksum-based deduplication and source metadata.
- Separate durable ingestion worker with bounded retries, lease recovery and atomic result publication.
- Physical PDF pages, extracted text spans, provisional chunks, protected original download/page preview and archive controls.
- PostgreSQL migrations, health endpoints and tests using an isolated PostgreSQL database.
- Audited source eligibility reviews, token-aware exact-span chunks, persistent Chroma generations and recoverable indexing jobs.
- Versioned English/Hindi OCR for flagged PDF pages, protected original comparison and append-only admin decisions.
- Protected English/Hindi/Hinglish Search with filters, source-page text inspection, historical-status notices and measured retrieval timings.

- Protected Ask with bounded local Ollama generation, validated claim/excerpt references, clarification/abstention, cancellation and private query history.
- Stable per-claim citations with original version/page/span inspection, separate provenance/support states and current-access checks.

## Stack

React, TypeScript, Vite and Tailwind CSS; FastAPI, SQLAlchemy, psycopg and Alembic; PostgreSQL; PyMuPDF; Sentence-Transformers with multilingual E5-small, CPU PyTorch and Chroma; Tesseract English/Hindi OCR; local Ollama Qwen3 4B Q4_K_M; Argon2id and JWT authentication. Dependencies are pinned in the backend lock and frontend package-lock.

## Setup and usage

See [Windows setup](docs/SETUP.md) for dependencies, private database configuration, migrations, startup and checks. Python 3.12, Node 22.12+ and PostgreSQL 18 are the documented baseline.

Run the API, frontend, ingestion worker, single-owner index service and answer worker in separate terminals. Open `http://127.0.0.1:5173/`. Sign in, then use `/#search` for exact passages or `/#ask` for questions explicitly about a dated historical document. Admin can upload PDF/TXT, inspect extraction, record evidence-backed eligibility reviews and queue index rebuilds. API documentation is at `http://127.0.0.1:8000/docs`.

## Current limitations

Claim support uses deterministic scope/value guards and a bounded heuristic judge using the same Qwen model as generation. This is not independent fact verification or complete semantic/legal interpretation. Pre-Part-6 answers remain not_evaluated; current source revocation withholds historical answer/excerpt content without rewriting private snapshots. Trust scores remain unavailable. Flagged PDF pages support bounded English/Hindi OCR with mandatory review and versioned extraction. Hindi output can contain language errors or hit the bounded output limit; failures publish no policy answer. Retrieval similarity is relevance, not correctness or current entitlement advice. A 0.78 cosine-similarity cutoff is a development heuristic, not calibrated abstention. Unreadable/unreviewed OCR remains excluded; source rights still require separate approval. Uploads have size/time/page/text limits but no malware scanner, OS parser sandbox or hard memory quota. Deployment is local development HTTP, not production-ready.

The local corpus contains four PDFs across three schemes: one reviewed historical PIB factsheet is indexed into nine token-aware passages; three original local-reference PDFs remain excluded. Permitted scope covers attributed PIB narrative text, excluding third-party graphics and linked-source content. Original PDFs, extracted corpus text, models, vectors, secrets and runtime data are excluded from Git. The small source-checked development set is not a held-out benchmark; see [recorded measurements](docs/VERIFICATION.md).

## Project records

- [Architecture](docs/ARCHITECTURE.md) and [API conventions](docs/API.md)
- [Maintainer state and roadmap](docs/MAINTAINER.md)
- [Recorded verification](docs/VERIFICATION.md)
- [Sources and licensing disclosures](docs/SOURCES.md) and [corpus manifest](docs/corpus_manifest.json)
- [Proposal requirement mapping](REQUIREMENTS_MATRIX.md)
