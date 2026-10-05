# Windows PowerShell setup

**Part 1 historical environment/setup record.** Current Part 2 adds a required PostgreSQL database, credentialed 127.0.0.1-only CORS and authentication. Follow [SETUP_PART2.md](SETUP_PART2.md) for current configuration, migrations, admin bootstrap, startup and tests; old phase-1 readiness assumptions below no longer apply.

## What was detected on 2026-10-05

| Item | Result | Needed when |
| --- | --- | --- |
| OS/shell | Windows 11 Home Single Language 64-bit, build 26300; PowerShell 7.6.5 | Now |
| CPU/RAM | Intel i5-13500HX, 14 cores/20 threads; 16,490,360 KiB usable memory (~15.7 GiB) | Recorded for future benchmarks |
| GPU | Intel UHD + NVIDIA RTX 4050 Laptop; nvidia-smi reports 6141 MiB VRAM | Optional later acceleration |
| Node/npm | Node 24.12.0 / npm 11.6.2 | Now; available |
| Git | 2.47.1.windows.1 | Now; available |
| Python | py launcher exists but reports no installed Pythons; Codex bundled Python 3.12.14 available | Now; project .venv created using bundled interpreter |
| Package managers | npm, pip in bundled/project Python, winget available; uv/Poetry absent from PATH | npm/pip enough now |
| PostgreSQL | psql not found on PATH; service installation not established | Part 2, not needed now |
| Docker | CLI 29.8.1; engine not reachable during inspection | Part 12, not needed now |
| Ollama | Not found on PATH | Part 5, not needed now |

WMI GPU AdapterRAM truncated the dedicated VRAM value; nvidia-smi was used instead. Initial sandbox blocked WMI/network and Vite ancestor-directory access; approved read/install/build commands resolved these limitations. No large AI model or infrastructure was installed.

## One-time setup

Use PowerShell. `npm.cmd` avoids PowerShell's npm.ps1 execution-policy issue. Virtual environment activation is unnecessary because commands invoke its Python directly. Do not relax system execution policy just to activate a venv.

```powershell
Set-Location 'C:\Users\thiss\OneDrive\Documents\ChatGPT\Gov_Policy_Agent'
```

**This laptop already has the project .venv and installed dependencies from Part 1.** For an independent Python installation, run these yourself when convenient:

```powershell
winget install --exact --id Python.Python.3.12 --source winget
# Open a fresh PowerShell after installation
py -3.12 --version
```

If winget is unavailable, install Microsoft's App Installer from the Microsoft Store, or download Python 3.12 from [Python's Windows releases](https://www.python.org/downloads/windows/). Select the 64-bit installer and include the Python launcher. Python 3.12 is the tested major/minor version; the exact bundled patch was 3.12.14. A fresh clone needs a venv:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock
Copy-Item .env.example .env
Set-Location frontend
npm.cmd ci
Copy-Item .env.example .env
Set-Location ..
```

Do not overwrite an existing .env. Defaults work without either file. Existing virtual environments retain the base interpreter path; after installing independent Python, rebuild the venv under a new name if needed, then switch after verification. Do not uninstall the Codex runtime while using this .venv.

If Node or Git is missing on another Windows machine:

```powershell
winget install --exact --id OpenJS.NodeJS.LTS --source winget
winget install --exact --id Git.Git --source winget
# Open a fresh terminal and confirm versions
node --version
npm.cmd --version
git --version
```

Use Node 22.12+ (tested on 24.12.0). Do not install uv, Poetry or additional package managers for this foundation.

## Start the two processes

Terminal 1, from the root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
Set-Location 'C:\Users\thiss\OneDrive\Documents\ChatGPT\Gov_Policy_Agent\frontend'
npm.cmd run dev
```

PowerShell helper scripts in scripts/ provide equivalent commands if your existing execution policy allows local scripts. For backend auto-reload while editing, add `--reload`; the verification server uses a single process without reload.

| URL | Expected result |
| --- | --- |
| http://127.0.0.1:5173 | Project title, planned languages, real backend connection status and retry |
| http://127.0.0.1:8000/health/live | status alive, project GOV-CS-028, phase 1; no AI loading |
| http://127.0.0.1:8000/health/ready | status ready; configuration validated; later services separately not required |
| http://127.0.0.1:8000/docs | Interactive Swagger UI (default UI assets need internet) |
| http://127.0.0.1:8000/openapi.json | OpenAPI specification |

The connected indicator is a **snapshot of the most recent check**, not continuous monitoring. Stop backend → click retry → Disconnected. Restart backend → retry → Connected. Requests time out after five seconds. Both servers bind loopback only. Ctrl+C stops each terminal.

## Configuration

Root .env: `GOV_APP_NAME`, `GOV_ENVIRONMENT` (`development` or `test`), `GOV_CORS_ORIGINS` (JSON array of explicit loopback HTTP origins with ports). Invalid settings fail application startup. PostgreSQL, Chroma and Ollama variables are deliberately absent until their phases.

Frontend .env: `VITE_API_BASE_URL=http://127.0.0.1:8000`. VITE_ values are public, bundled into frontend code; never put passwords/tokens there. Restart Vite after changing them; rebuild for production. The sample .env files are safe; real .env files are ignored.

Allowed origins default to http://localhost:5173 and http://127.0.0.1:5173. If testing production preview (`npm.cmd run preview`, port 4173), add the exact preview origin to root CORS settings and restart backend. Preview is a build check, not final deployment packaging.

## Verify

From root:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
Invoke-RestMethod http://127.0.0.1:8000/health/ready
Set-Location frontend
npm.cmd run typecheck
npm.cmd run build
```

The API must be running for Invoke-RestMethod. Unit tests do not require a running server. `scripts/verify.ps1` runs dependency checks, tests and build with failure propagation. See [VERIFICATION.md](VERIFICATION.md) for executed checks.

Dependency updates: change direct versions in backend/requirements.in, resolve in a clean Python 3.12 venv, test, then regenerate requirements.lock using `python -m pip freeze`. Install the lock in a fresh venv and verify before accepting an update. The backend lock pins all resolved dependencies; it is not a wheel hash lock or a cross-platform compatibility guarantee. npm updates require regenerated package-lock and `npm.cmd ci` plus build checks. Never delete lockfiles to hide a version conflict.

## Later prerequisites — instructions only, do not install now

- **Part 2 PostgreSQL:** use the Windows installer linked by [PostgreSQL's official Windows page](https://www.postgresql.org/download/windows/). Install server and command-line tools, choose a local password privately, keep port 5432 local, and skip optional Stack Builder packages. Verify via the installed `bin\psql.exe --version`; the major version will be selected and documented in Part 2. No password belongs in chat or Git.
- **Part 5 Ollama:** use [Ollama's official Windows installer](https://ollama.com/download/windows); reopen PowerShell and run `ollama --version`. Do not run `ollama pull` until the model benchmark plan is agreed in Part 5.
- **Part 7 Tesseract:** follow Windows builds linked by [Tesseract's installation documentation](https://tesseract-ocr.github.io/tessdoc/Installation.html), add the executable directory to PATH, install English/Hindi traineddata, then run `tesseract --version` and `tesseract --list-langs` (must list eng/hin). No OCR dependency is required now.
- **Part 12 Docker:** already installed here. Launch Docker Desktop yourself, ensure WSL2 support is enabled, then run `docker version` and `docker compose version`. If WSL is missing, use `wsl --install` from an administrator terminal and reboot when prompted. Follow [Docker's Windows setup](https://docs.docker.com/desktop/setup/install/windows-install/); use only a license-eligible free configuration. Compose/GPU container setup will be verified in Part 12.

## Troubleshooting and Git authentication

If ports are occupied, identify the process with `Get-NetTCPConnection -LocalPort 8000,5173 -ErrorAction SilentlyContinue`; do not kill unrelated processes. Stop the relevant terminal or change ports and update frontend/CORS together. Vite uses `--strictPort` to prevent silent port changes. In Codex, permission-related build/network errors may require an approved command; they do not mean dependencies are missing.

Git origin must be https://github.com/shashwatmishra18/Gov_Policy_Agent.git before push. If a push requests authentication, use Git Credential Manager's normal browser sign-in. Alternatively install GitHub CLI using `winget install --exact --id GitHub.cli --source winget`, then run `gh auth login --hostname github.com --git-protocol https --web` and `gh auth setup-git`. Never paste tokens or passwords into chat. Fetch and compare main before retrying; never force-push. Part 1 must pass verification before a finished-phase commit is pushed.

## Official API references consulted

- [FastAPI settings](https://fastapi.tiangolo.com/advanced/settings/) and [Pydantic settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/): BaseSettings, environment prefix, dotenv and field validation.
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/) and [testing](https://fastapi.tiangolo.com/tutorial/testing/): explicit browser origins, CORSMiddleware and TestClient.
- [FastAPI versions](https://fastapi.tiangolo.com/deployment/versions/): pin and test compatibility; the fully resolved lock captures the tested transitive set.
- [Vite guide](https://vite.dev/guide/) and [Tailwind Vite integration](https://tailwindcss.com/docs/installation/using-vite): TypeScript/React build and Tailwind v4 plugin plus CSS import.

Consulted 2026-10-05. Package versions are the exact tested set, not a claim that every package is the newest release.
