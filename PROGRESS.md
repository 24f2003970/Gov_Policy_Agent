# Progress

Updated 2026-10-05 (Asia/Kolkata). Current scope: Part 2 only; Part 1 completed previously.

## Implemented

- Windows/CPU/RAM/GPU/tool inventory; project-local isolated Python environment.
- FastAPI health routes, validated settings, explicit local CORS, request IDs and application error format.
- Responsive React/TypeScript/Vite/Tailwind screen with real readiness fetch, loading, failure, timeout and retry.
- Full 34-page proposal read; requirement mapping, six trust dimensions and adaptations documented.
- Safe environment examples; ignores for proposal, all PDFs, secrets, uploaded files, models and runtime data.
- Exact dependency locks, health/security-path tests and PowerShell startup/verification helpers.
- Architecture and initial relational design, 12-part roadmap, beginner walkthrough and setup instructions.

## Verification/release gate

**Part 1 complete.** See docs/VERIFICATION.md for actual checks. All required technical checks passed: 14 backend tests, clean backend lock install and pip check, npm ci, TypeScript and production build, real connected/disconnected/recovered browser states, and responsive review. The staged diff and public file tree were reviewed. Foundation commit `e8a41e16ba7e1c3b298724a05930d5fd6aae7c9b` was pushed to main and independently confirmed by remote refs. This record is a documentation follow-up to that verified commit; no future phase was implemented.

## Historical Part 1 limits and user actions

- Independent Python install absent; current .venv uses Codex bundled Python. Install Python 3.12 later for an independent setup (docs/SETUP.md).
- PostgreSQL/Ollama not found on PATH; Docker engine unavailable during inspection. They are not needed in this phase.
- No AI models, corpus ingestion, authentication, database migrations, embeddings or RAG implemented. No quality metrics or trust scores measured.
- Correct origin and initial main configured, remote rechecked empty before publishing. Repository-local commit email uses GitHub noreply for privacy.

## Part 2 completed implementation and verification

Implemented SQLAlchemy users/auth_sessions/auth_throttles, explicit Alembic migration, Argon2id/JWT authentication, row-locked rotating refresh sessions, live revocation/status/role checks, CSRF/CORS, durable login throttling, private provisioning/admin CLI, profile/admin endpoints and minimal React auth pages. Foundation UI/liveness are preserved; readiness now requires PostgreSQL/schema and signing configuration.

All 32 backend tests passed, including 16 real PostgreSQL cases and 16 foundation/config/security regressions. pip check, TypeScript and production build passed. PostgreSQL 18.6 folder/service verified; localhost-only listeners are 127.0.0.1 and ::1. Dedicated gov_app/gov_policy and gov_test/gov_policy_test connections verified without superuser/role-creation/database-creation/replication privileges. Explicit application migration and repeated upgrade succeeded; both schemas are current.

Real browser registration, wrong-password error, login, profile save, reload restoration, normal-user admin denial, logout/protected-page denial and privately entered admin login/access all passed. Session restoration also survived a real backend process restart (PID 22712 to 13620). The first administrator was bootstrapped by the user with hidden input; no private account details or passwords are recorded in Git. See docs/VERIFICATION.md for release evidence and docs/SETUP_PART2.md for reproducible commands.

Part 2 release checks and the 34-file staged review passed. The resulting main release commit is identified by git log and the publication result. Future parts require separate prompts. Remaining limits: local development HTTP only, upstream TestClient deprecation warning, bounded refresh history may require re-login, and cross-tab fallback without Web Locks may revoke racing sessions. Public deployment/security evaluation remains Parts 11–12.

No document ingestion, embeddings, AI models, RAG, citations, trust scoring or dashboards were implemented. Future parts require separate user prompts.
