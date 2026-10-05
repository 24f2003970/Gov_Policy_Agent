# Multilingual Government Policy Assistant

**GOV-CS-028** · B.Tech project · Part 2 PostgreSQL and authentication

A local application being developed to answer English, Hindi and practical Hinglish policy questions from verified official evidence. The final system will support grounded RAG, claim-level citations and an experimental evidence-quality index. These capabilities are **planned**, not implemented or measured yet.

The Part 1 foundation is preserved. Part 2 adds PostgreSQL persistence, explicit Alembic migrations, registration/login, rotating refresh sessions, protected profiles and server-enforced user/admin roles. Access tokens stay in frontend memory; refresh tokens use HttpOnly cookies. Database integration and browser verification status is recorded in [PROGRESS.md](PROGRESS.md). There are no policy answers, corpus documents or AI model downloads yet.

## Start on Windows PowerShell

From the repository root, after private PostgreSQL setup in [docs/SETUP_PART2.md](docs/SETUP_PART2.md):

```powershell
# Terminal 1
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --no-proxy-headers
```

```powershell
# Terminal 2
Set-Location frontend
npm.cmd run dev
```

Open http://127.0.0.1:5173. The status should show **Connected · Foundation ready** and a request ID. It reflects the last explicit health check; use the retry button after stopping or restarting the backend. API docs: http://127.0.0.1:8000/docs. Stop each terminal with Ctrl+C.

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
frontend/src/    foundation screen, health client and auth pages
docs/           setup, architecture, verification and beginner explanations
scripts/        PowerShell startup and verification helpers
tests/          foundation/security tests and real PostgreSQL auth tests
```

## Project records

- [Current PostgreSQL/auth setup](docs/SETUP_PART2.md) and [Part 1 environment record](docs/SETUP.md)
- [Architecture and planned relational design](docs/ARCHITECTURE.md)
- [Beginner code walkthrough and viva](docs/WALKTHROUGH.md)
- [Roadmap](PROJECT_PLAN.md), [progress](PROGRESS.md), [decisions](DECISIONS.md)
- [Proposal requirement mapping](REQUIREMENTS_MATRIX.md)
- [Executed verification](docs/VERIFICATION.md)

The local 34-page proposal was read as a requirements reference. It is ignored by Git and must never become chatbot evidence. Uploaded documents, secrets, local data and model weights are also ignored. No accuracy, novelty, publication or production-scale claims have been established.
