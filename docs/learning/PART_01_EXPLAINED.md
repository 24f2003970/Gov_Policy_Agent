# Part 1 samjho: project ki working foundation

## 1. Is part ka purpose

Socho humein ek library banani hai. Books arrange karne se pehle building, reception aur electricity check karna zaroori hai. Part 1 ne project ki woh foundation banayi: browser screen, Python API, configuration, health checks, tests aur setup instructions.

Yeh historical Part 1 explanation hai. Aaj same project mein Part 2 authentication aur Part 3 ingestion bhi hain. Parts 1/2 ko dobara build nahi kiya gaya. Part 1 ke time database ya AI required nahi tha; **current readiness ke liye migrated PostgreSQL required hai**.

## 2. Basic concepts, everyday examples

| Term | Simple meaning | Example |
| --- | --- | --- |
| Frontend | Jo screen user dekhta aur click karta hai | Library ka reception desk |
| Backend | Screen ke request ko process karne wala program | Reception ke peeche working staff |
| API | Dono programs ke beech agreed request/response interface | Menu mein available services aur unke names |
| HTTP | Browser/server communication ka protocol | Request bhejne aur reply paane ka standard format |
| GET | Information mangne wala HTTP method | “Library open hai?” |
| JSON | Named values ka readable data format | `{"status":"alive"}` |
| Port | Ek computer par program ka network entry number | Same building ke different room numbers |
| localhost / loopback | Isi computer ko address karna | Apne ghar ke andar baat karna |
| Dependency | Library/package jis par apna program depend karta hai | Building ke liye electrical components |
| Virtual environment | Project ki separate Python package environment | Har project ka apna toolbox |
| Lockfile | Tested packages ke exact versions ka record | Toolbox ke exact model numbers ki list |
| Git commit | Code ka named snapshot | Notebook ka dated saved edition |
| CORS | Browser ko kis origin se API read karne ki permission hai | Approved reception desks ki list |

Origin mein protocol, hostname aur port tino aate hain. `http://127.0.0.1:5173` aur `http://127.0.0.1:8000` different origins hain. Current project mein 127.0.0.1 consistently use karo; localhost browser origin Part 2 se approved nahi hai.

## 3. Click se result tak flow

1. Frontend Vite server port 5173 par page serve karta hai.
2. React screen backend connection check shuru karti hai. Screen loading state dikhati hai.
3. [health.ts](../../frontend/src/health.ts) API ke `/health/ready` ko GET request bhejta hai.
4. [main.py](../../backend/app/main.py) readiness response aur request ID return karta hai.
5. Client response ka status aur expected structure validate karta hai.
6. Success par Connected indicator; server unavailable/invalid response par useful error aur retry control milta hai.
7. “Check connection again” fresh request bhejta hai. Indicator continuously background monitoring nahi karta.

Part 1 ke time successful app configuration hi readiness requirement thi. Aaj isi route par database connection aur current auth/document schema bhi check hota hai. Liveness ab bhi database se independent hai.

## 4. Important files ka connection

| Actual file | Kya karti hai |
| --- | --- |
| [backend/app/main.py](../../backend/app/main.py) | FastAPI app, health endpoints, request IDs, errors, CORS; later parts ke routers bhi yahin connect hain |
| [backend/app/config.py](../../backend/app/config.py) | Environment settings validate karti hai; current DB/auth/storage fields later parts se aaye |
| [frontend/src/App.tsx](../../frontend/src/App.tsx) | Preserved foundation screen aur connection states |
| [frontend/src/health.ts](../../frontend/src/health.ts) | Readiness HTTP request, timeout signal, response validation |
| [frontend/src/main.tsx](../../frontend/src/main.tsx) | React entry; aaj AuthApp ko mount karta hai, jisme foundation screen included hai |
| [scripts/start-backend.ps1](../../scripts/start-backend.ps1) | Root directory se correct API startup |
| [scripts/start-frontend.ps1](../../scripts/start-frontend.ps1) | Frontend development server startup |
| [scripts/verify.ps1](../../scripts/verify.ps1) | Dependency, backend tests aur frontend build checks |
| [backend/requirements.in](../../backend/requirements.in) | Direct Python dependency choices |
| [backend/requirements.lock](../../backend/requirements.lock) | Exact complete Python package versions |
| [frontend/package-lock.json](../../frontend/package-lock.json) | Exact npm dependency tree |
| [tests/test_health.py](../../tests/test_health.py) | Health, request IDs, CORS, configuration aur error behavior tests |
| [.gitignore](../../.gitignore) | Secrets, PDFs, dependency folders, runtime files Git se exclude karta hai |

## 5. Functions, endpoints, input/output

| Name | Input | Result |
| --- | --- | --- |
| `create_app(settings)` | Validated settings, ya default settings | Configured FastAPI application |
| `request_context` | Incoming HTTP request | Server-generated UUID request ID; response headers; safe failure handling |
| `error_response` | HTTP status, error code/message | Consistent `error.code/message/request_id` JSON |
| `GET /health/live` | No body | HTTP 200, process alive, project ID and current phase |
| `GET /health/ready` | No body | Part 1: validated config; now 200 when DB/schema/signing ready, otherwise 503 |
| `fetchHealth(signal)` | Abort signal | Validated health result/request ID, ya readable error |
| `/docs` | Browser visit | Interactive Swagger API documentation |
| `/openapi.json` | GET request | Machine-readable API specification |

Part 1 ne **koi database table create nahi ki**. Request ID diagnostic tracking ke liye hai, password ya login token nahi. Error mein original secret input ya internal exception reflect nahi hoti. CORS preflight framework response application error envelope se separate ho sakta hai.

## 6. Technology choices aur limits

React screen ko components mein organize karta hai. TypeScript development time par type mistakes pakadta hai; woh server response ko automatically trustworthy nahi banata, isliye health client validation bhi karta hai. Tailwind utility classes styling ke liye hain. Vite local development/build tool hai.

FastAPI Python request handling aur OpenAPI generation deta hai. Pydantic settings invalid configuration reject karti hain. Native fetch use hua; extra Axios/routing framework add nahi hua. Small local project ke liye ek API process manageable hai.

Current `.venv` Codex bundled Python 3.12 par based hai; is laptop par independent Python setup optional future portability task hai. Docker engine available nahi tha, isliye foundation Docker-dependent nahi bani. Swagger ke default external assets ke liye Internet lag sakta hai.

## 7. Exact current commands

PowerShell terminal mein pehle repository root:

```powershell
Set-Location 'C:\Users\thiss\OneDrive\Documents\ChatGPT\Gov_Policy_Agent'
```

API ke liye Terminal 1:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Expected: `Uvicorn running on http://127.0.0.1:8000`. Agar address already in use aaye, existing project API terminal use karo ya usmein Ctrl+C karke ek hi copy start karo.

Frontend ke liye Terminal 2, root se:

```powershell
Set-Location frontend
npm.cmd run dev
```

Expected: Vite local URL `http://127.0.0.1:5173/`. `npm.cmd` PowerShell execution-policy confusion avoid karta hai. Venv activate karna required nahi: command correct Python executable directly use karta hai.

Verification ke liye root se separate terminal:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
Set-Location frontend
npm.cmd run build
```

Current full tests mein real PostgreSQL required hai. Current migrations/worker setup ke liye [Part 3 setup](../SETUP_PART3.md) dekho; historical Part 1 instructions ko current readiness prerequisites samajhkar use mat karo.

## 8. App mein check kaise karein

Browser mein `http://127.0.0.1:5173/#home` kholo. API aur migrated DB running hain toh Connected indicator aayega. API terminal stop karne ke baad check button dabao: failure aana chahiye. Restart karke button dabao: connection recover hona chahiye. `/health/live` open karne par JSON milta hai; `/docs` par endpoint list.

## 9. Actual verification record

[VERIFICATION.md](../VERIFICATION.md) mein recorded Part 1 evidence: **14 backend tests**, clean locked dependency install/pip check, npm ci, typecheck/build, actual connected/disconnected/recovered browser states aur responsive review passed. Foundation commit `e8a41e16ba7e1c3b298724a05930d5fd6aae7c9b` pushed tha.

Later phases mein health expectations update hui hain; current suite historical Part 1 count se different hai. Part 3 release record current total batata hai. Original five-second client timeout exists, lekin distinct delayed-server browser timeout scenario Part 1 mein separately exercise nahi hua tha. Tests ko AI-answer correctness ya performance benchmark mat samjho.

## 10. Common errors

| Problem | Simple fix |
| --- | --- |
| Failed to fetch | API running hai? Correct 8000 URL? 127.0.0.1 consistently use hua? |
| Ready 503 but live 200 | Current DB/config/migrations check karo; server alive hona dependencies ready hone jaisa nahi |
| Python module missing | Root se existing .venv executable use karo; locked requirements install karo |
| npm.ps1 execution error | `npm.cmd` use karo; system security policy relax mat karo |
| Port already in use | Same server ki multiple copies mat chalao |
| Wrong directory | Root command root se; npm command frontend directory se |

## 11. Beginner viva

1. **Frontend aur backend mein difference?** Frontend screen hai; backend requests process karta hai.
2. **API kya hai?** Programs ke communication ka agreed interface.
3. **JSON kya hai?** Named values ka structured data format.
4. **Liveness/readiness alag kyun?** Process running ho sakta hai jab database unavailable ho.
5. **Request ID kyun?** Ek request ki problem trace karne ke liye, secrets print kiye bina.
6. **CORS kyun?** Browser ko approved origins ki permission dene ke liye; yeh login ka replacement nahi.
7. **Venv kyun?** Project packages ko doosre projects se separate rakhne ke liye.
8. **Lockfile kyun?** Same tested package versions reproduce karne ke liye.
9. **Gitignore kya karta hai?** Private/runtime files ko accidentally commit hone se bachata hai.
10. **Part 1 ne AI answer diya?** Nahi; sirf working foundation di.

## 12. Bolkar explain karne ka short version

“Part 1 mein maine React frontend aur FastAPI backend ki working foundation banayi. Browser real API se health status leta hai. Liveness process ko aur readiness required dependencies ko check karti hai. Request IDs, safe errors, validated settings aur pinned dependencies setup ko reproducible banate hain. Is part mein AI ya policy answers implement nahi hue.”
