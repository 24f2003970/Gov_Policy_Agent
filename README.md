# Multilingual Government Policy Assistant

GOV-CS-028 is a B.Tech student project for exploring document-grounded government policy question answering in English, Hindi and Hinglish. The current application provides authentication and document ingestion. Question answering and retrieval are not implemented yet.

## Implemented features

- Registration, login, rotating sessions, language preference and server-enforced user/admin roles.
- Admin PDF/UTF-8 TXT upload, immutable document versions, checksum-based deduplication and source metadata.
- Separate durable ingestion worker with bounded retries, lease recovery and atomic result publication.
- Physical PDF pages, extracted text spans, provisional chunks, protected original download/page preview and archive controls.
- PostgreSQL migrations, health endpoints and tests using an isolated PostgreSQL database.

## Stack

React, TypeScript, Vite and Tailwind CSS; FastAPI, SQLAlchemy, psycopg and Alembic; PostgreSQL; PyMuPDF; Argon2id and JWT authentication. Dependencies are pinned in the backend lock and frontend package-lock.

## Setup and usage

See [Windows setup](docs/SETUP.md) for dependencies, private database configuration, migrations, startup and checks. Python 3.12, Node 22.12+ and PostgreSQL 18 are the documented baseline.

Run the API, frontend and ingestion worker in separate terminals. Open `http://127.0.0.1:5173/`. Register a normal account or sign in with an existing administrator. Admin can select a PDF/TXT file, enter source metadata, upload it and inspect job status, pages and original preview. Queued jobs require the worker to run. API documentation is at `http://127.0.0.1:8000/docs`.

## Current limitations

No embeddings, semantic retrieval, AI answers, OCR, validated citations or trust scores. Low-text/scanned pages remain OCR-pending; mixed PDFs are partial. Digital text order, table layout and encoding need source-page review. Uploads have size/time/page/text limits but no malware scanner, OS parser sandbox or hard memory quota. Deployment is local development HTTP, not production-ready.

The inspected local corpus contains three official-origin PDFs across three schemes, 164 pages and 398 provisional chunks. Reproduction permissions are not obtained; all are local-reference-only and none is eligible for future retrieval. Original PDFs, extracted corpus text, secrets and runtime data are excluded from Git. No measured answer-quality or scalability claims are made.

## Project records

- [Architecture](docs/ARCHITECTURE.md) and [API conventions](docs/API.md)
- [Maintainer state and roadmap](docs/MAINTAINER.md)
- [Recorded verification](docs/VERIFICATION.md)
- [Sources and licensing disclosures](docs/SOURCES.md) and [corpus manifest](docs/corpus_manifest.json)
- [Proposal requirement mapping](REQUIREMENTS_MATRIX.md)
