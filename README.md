# Multilingual Government Policy Assistant

**GOV-CS-028** · B.Tech project · Part 1 runnable foundation

A local application being developed to answer English, Hindi and practical Hinglish policy questions from verified official evidence. The final system will support grounded RAG, claim-level citations and an experimental evidence-quality index. These capabilities are **planned**, not implemented or measured yet.

Part 1 provides a FastAPI backend and a responsive React/TypeScript/Tailwind screen that calls the real readiness endpoint. It includes validated environment settings, restricted local CORS, request IDs, consistent application errors and health tests. There are no policy answers, corpus documents, authentication or AI model downloads in this phase.

## Start on Windows PowerShell

From the repository root, after the one-time setup in [docs/SETUP.md](docs/SETUP.md):

```powershell
# Terminal 1
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2
Set-Location frontend
npm.cmd run dev
```

Open http://127.0.0.1:5173. The status should show **Connected · Foundation ready** and a request ID. It reflects the last explicit health check; use the retry button after stopping or restarting the backend. API docs: http://127.0.0.1:8000/docs. Stop each terminal with Ctrl+C.

```powershell
# Run from the repository root
.\.venv\Scripts\python.exe -m pytest -q
Set-Location frontend
npm.cmd run build
```

## Layout

```text
backend/app/     configuration and FastAPI application
frontend/src/    React screen and real health client
docs/           setup, architecture, verification and beginner explanations
scripts/        PowerShell startup and verification helpers
tests/          backend health, CORS, errors and configuration tests
```

## Project records

- [Setup and missing prerequisites](docs/SETUP.md)
- [Architecture and planned relational design](docs/ARCHITECTURE.md)
- [Beginner code walkthrough and viva](docs/WALKTHROUGH.md)
- [Roadmap](PROJECT_PLAN.md), [progress](PROGRESS.md), [decisions](DECISIONS.md)
- [Proposal requirement mapping](REQUIREMENTS_MATRIX.md)
- [Executed verification](docs/VERIFICATION.md)

The local 34-page proposal was read as a requirements reference. It is ignored by Git and must never become chatbot evidence. Uploaded documents, secrets, local data and model weights are also ignored. No accuracy, novelty, publication or production-scale claims have been established.
