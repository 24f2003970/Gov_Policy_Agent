# Part 1 verification record

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

All required Part 1 technical checks passed. Publication evidence is recorded below after commit/push; no unrun check is counted as passing.

## What remains outside Part 1

No PostgreSQL/Chroma/Ollama integration, GPU inference, OCR, authentication, RAG, policy citations, score calibration or corpus quality evaluation was executed. No AI dependencies were downloaded. Swagger UI uses the framework's default external assets; health and frontend work locally after dependency installation.

The health indicator reports the last user-triggered check, not ongoing background monitoring. Loading and five-second timeout handling exist in the code; distinct delayed-response timeout behavior has not yet been exercised in the browser.
