# Part 1 verification record

Part 1 evidence below is historical. Current Part 2 verification is recorded at the end; Part 2 is not considered complete until required real PostgreSQL/browser checks pass.

Date: 2026-10-05, Windows 11 / PowerShell 7.6.5. Python 3.12.14 in project .venv; Node 24.12.0 / npm 11.6.2.

| Executed check | Observed result |
| --- | --- |
| Git current workspace / status / remote | Empty initialized repository on unborn master; no user code overwritten; remote ls-remote returned no refs |
| Proposal read | All 34 physical pages extracted and read; page 15 reread with UTF-8 after terminal encoding error |
| Hardware inventory | WMI CPU/RAM/OS and nvidia-smi actual VRAM checked |
| Python install/dependency check | Pinned dependency install succeeded; pip check found no broken requirements |
| Backend pytest after Starlette pin | 14 passed; one upstream anyio BlockingPortal alias deprecation warning (does not fail tests) |
| Frontend TypeScript/build | tsc --noEmit passed; Vite production build passed, 30 modules transformed |
| Real browser startup | Connected · Foundation ready observed at 127.0.0.1:5173 with API-generated UUID |
| Backend shutdown + browser retry | Disconnected / Failed to fetch observed; no cached success shown after retry |
| Ignore check | git check-ignore confirmed proposal PDF, .env, .venv and node_modules excluded |
| Backend lock installed in clean .venv-lockcheck | All 24 pinned packages installed; pip check passed; 14 tests passed again. One upstream deprecation warning and a Windows pytest-cache permission warning; test execution succeeded |
| Frontend locked reinstall | npm ci installed 82 packages, then TypeScript and production build passed again. First attempt hit a native file lock because Vite was running; stopping Vite resolved it |
| Actual HTTP health requests | Invoke-RestMethod confirmed live=alive and ready=ready with current/optional dependency breakdown |
| Backend restart + browser reload | Connected recovered with a fresh request UUID |
| Responsive review | Mobile/default viewport and 1366px desktop checked; DOM page width did not exceed viewport, desktop full-page layout visually inspected; temporary viewport reset |
| Remote prepublication recheck | Origin matched requested URL; ls-remote still returned no refs |

All required Part 1 technical checks passed; no unrun check is counted as passing.

## Publication evidence

- Reviewed/staged exactly 33 intended files; staged diff whitespace check passed.
- Created initial main and configured origin as https://github.com/shashwatmishra18/Gov_Policy_Agent.git; remote rechecked empty before initial push.
- Foundation commit: `e8a41e16ba7e1c3b298724a05930d5fd6aae7c9b`, `feat: build verified Part 1 FastAPI and React foundation`.
- `git push -u origin main` succeeded; `git ls-remote origin refs/heads/main` independently returned that exact hash.
- Clean tracked working tree after push; all 33 committed paths reviewed. No PDF, actual .env, dependency directory, private user record or model weight in the Git tree.
- This release record is a subsequent documentation-only commit. Use `git log -1` for the final documentation revision; foundation code/tests remain unchanged.

## What remains outside Part 1

No PostgreSQL/Chroma/Ollama integration, GPU inference, OCR, authentication, RAG, policy citations, score calibration or corpus quality evaluation was executed. No AI dependencies were downloaded. Swagger UI uses the framework's default external assets; health and frontend work locally after dependency installation.

The health indicator reports the last user-triggered check, not ongoing background monitoring. Loading and five-second timeout handling exist in the code; distinct delayed-response timeout behavior has not yet been exercised in the browser.

## Part 2 executed verification (2026-10-05)

- Existing repository/docs/code inspected; no applicable AGENTS.md found. Origin matched requested repository; fetch showed no remote changes; clean initial main.
- PostgreSQL initially absent in PATH, services, standard install folders and registry. User's initial installation report was checked and corrected; no false DB completion claimed.
- Trusted winget selected PostgreSQL 18.6-5 from official EDB URL. Delivery Optimization download stalled; same 414,966,472-byte installer downloaded directly. SHA256 exactly matched the trusted manifest and Authenticode reported valid EnterpriseDB signer before launch.
- Native installation verified at C:\Program Files\PostgreSQL\18; psql reports PostgreSQL 18.6. Private configure saved localhost-only settings, and the service was restarted through Windows UAC. postgresql-x64-18 is running; actual listeners are 127.0.0.1 and ::1 only on port 5432. pg_isready reports accepting connections. Authenticated application/test connections were subsequently verified; no extra Stack Builder packages are required.
- Existing bundled-Python .venv preserved; pinned auth/DB dependencies installed; pip check passed; complete requirements.lock regenerated.
- Final complete suite: 32 passed in 7.44 seconds, including 16 foundation/config/security checks and 16 real PostgreSQL cases. One upstream Starlette/anyio BlockingPortal deprecation warning remains. Added Alembic path_separator=os to resolve its config warning, then reran the complete suite.
- Frontend tsc/build passed (32 modules); package-lock unchanged. First build found Web Locks generic typing issue; fixed and passing build rerun.
- Private configure succeeded; independent authenticated checks confirmed gov_policy/gov_app and gov_policy_test/gov_test, no SUPERUSER/CREATEDB/CREATEROLE/REPLICATION, localhost-only server settings and current schemas. Exactly one private first admin exists, created through hidden-input CLI by the user.
- Application Alembic upgrade head, repeated upgrade and current succeeded: 0001_auth (head). Test fixture migrated from empty dedicated test DB and repeated upgrade. No application DB reset, SQLite or mocked auth completion.
- Real PostgreSQL tests passed: normalization/duplicates, Argon2id/no response secrets, password/input/role validation, login/profile/current role checks, expired/tampered/wrong issuer/audience/algorithm/missing claims, transactional concurrent rotation/replay, logout/revocation, disabled/expired sessions, CSRF/cookie flags, durable throttle and app recreation, missing migration and unreachable DB readiness.
- Browser: registered a synthetic normal user, observed wrong-password error, successful login and account details, saved Hinglish preference, reloaded and restored session/preference. Admin navigation was absent; direct #admin returned Admin role required. Logout removed authenticated navigation and direct #account showed Sign in required.
- Actual process restart: stopped this project's backend PID 22712, started PID 13620 with --no-proxy-headers, then reloaded the browser. Persisted session restored; protected requests succeeded. This is separate from TestClient app recreation tests.
- User privately entered first-admin credentials in browser. Admin navigation appeared and #admin visibly returned Admin access confirmed by the backend. Local screenshots runtime/screenshots/part2-user-admin-denied.png and part2-admin-confirmed.png are ignored and contain no password/token.
- Current /health/ready returns HTTP 200 with connected_schema_current and authentication configured; Chroma/Ollama not required. The unavailable/missing-schema tests return 503 while liveness remains 200.
- Final frontend typecheck and production build passed (32 modules). A sandbox esbuild directory-access failure was resolved by an approved elevated rerun; no code workaround required. npm package-lock is unchanged. pip check reports no broken requirements.

## Part 2 publication review

Required database/browser checks passed before publication. Exactly 34 intended files staged; whitespace check passed. Review excludes .env, PDFs, installer, runtime screenshots/scripts, dependency directories and dist; these stay ignored. An in-memory comparison against private configuration/admin identity confirmed those values are absent from staged source/docs. Remote main was refetched and matched HEAD before the release commit. The release is published to main without force; use git log -1 and the independently checked remote main ref for the resulting release hash.
