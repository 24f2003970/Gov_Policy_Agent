# VS Code mein project run karne ka runbook (Hinglish)

Project: **GOV-CS-028 — Government Policy Assistant**

## Sir ke saamne dikhane ke liye 60-second project intro

“Yeh local, document-grounded Government Policy Assistant hai. Frontend React + Vite hai; backend FastAPI hai. PostgreSQL users, uploads, jobs aur answers store karta hai. Admin PDFs/TXT upload karta hai; ingestion worker unhe extract karta hai; index service reviewed passages ko multilingual E5/Chroma mein index karti hai; Ask mein local Ollama/Qwen answer banata hai. App cited source/page aur evidence limitations dikhata hai. Yeh student prototype hai, official Government of India service nahi. Historical source current eligibility ki guarantee nahi deta.”

**Current demo corpus limitation:** abhi sirf ek source active reviewed/eligible index mein hai: 12 Oct 2024 ki PIB PM Internship Scheme factsheet. Baaki scheme PDFs ko Ask ke jawab ke roop mein demo mat karna; woh exclude/unreviewed ho sakte hain. Verified question set aur tested answers [PRESENTATION_QA.md](PRESENTATION_QA.md) mein hai.

## Kal isi laptop par VS Code se run karna (recommended)

Is machine par `.venv`, private `.env`, PostgreSQL database, model files aur source data pehle se prepared hain. **Unhe dobara install, configure, migrate, bootstrap ya reset mat karna.** VS Code ka open folder project root hona chahiye—jahan `backend`, `frontend`, `scripts`, `.venv` folders dikhen:

`C:\Users\satya\Downloads\Compressed\Gov_Policy_Agent-main\Gov_Policy_Agent-main`

### Step 1 — VS Code mein project root kholna

VS Code → **File → Open Folder** → upar diya folder select karo. Phir **Terminal → New Terminal**.

Prompt ka end project root par hona chahiye. Agar nahi, terminal mein:

```powershell
cd "C:\Users\satya\Downloads\Compressed\Gov_Policy_Agent-main\Gov_Policy_Agent-main"
```

Check:

```powershell
Get-Location
```

Expected path ka end `Gov_Policy_Agent-main\Gov_Policy_Agent-main` hoga. `backend`, `frontend`, `scripts` folders hon tabhi next step.

### Step 2 — dekho kaunse services already chal rahe hain

```powershell
.\scripts\native.ps1 status
```

Expected running case:

```text
api managed running
frontend managed running
worker managed running
index managed running
rag managed running
```

`managed running` ka matlab process managed hai; yeh akela browser/API readiness ka proof nahi.

### Step 3 — dependencies/config/model pins check karo

```powershell
.\scripts\native.ps1 preflight
```

Expected:

```text
Native dependency/config/schema/model-manifest/OCR preflight passed; no model loaded.
```

Is command se model load nahi hota. Agar check fail ho, error ko note karke setup/logs investigate karo; `.env` overwrite ya database reset mat karna.

### Step 4 — app ke missing services start karo

```powershell
.\scripts\native.ps1 start
```

Yeh pehle preflight chalata hai, phir `api`, `frontend`, ingestion `worker`, `index`, aur `rag` ko managed background owners ke roop mein start karta hai. Example output:

```text
Native dependency/config/schema/model-manifest/OCR preflight passed; no model loaded.
api started; readiness may take time, inspect status/System status
frontend started; readiness may take time, inspect status/System status
worker started; readiness may take time, inspect status/System status
index started; readiness may take time, inspect status/System status
rag started; readiness may take time, inspect status/System status
```

Agar koi service pehle se chal rahi hai to output `already running; no duplicate started` ho sakta hai—yeh normal hai. `native.ps1` ke saath same service ko alag terminal mein dobara launch mat karna.

### Step 5 — process aur API readiness verify karo

```powershell
.\scripts\native.ps1 status
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

Har service ke aage `managed running` expected hai. API JSON mein `status : ready` aur `project_id : GOV-CS-028` expected hai. `health/ready` database/schema/auth check karta hai; Search/Ask ke liye index aur local answer worker bhi chahiye.

Index readiness check:

```powershell
Invoke-RestMethod http://127.0.0.1:8011/health/ready
```

Expected JSON: `status : ready`.

### Step 6 — browser mein project kholo

```text
http://127.0.0.1:5173/#ask
```

Login screen aaye to apne **registered account email/password** se login karo. Password chat ya screenshot mein mat likho. Existing account ho to `bootstrap-admin` ya database configure command mat chalao.

### Step 7 — presentation ke liye ek verified question run karo

Language **English** select karo, phir yeh single-fact question paste karo:

```text
According to the 12 October 2024 PIB factsheet, what age group was the pilot intended for?
```

Expected answer: `21–24 years`, source page **2**, citation coverage **100%**. Citation kholkar source quote/page sir ko dikhao. Hindi demo ke liye language **Hindi** select karke:

```text
2024 की PIB factsheet के अनुसार, PM Internship Scheme के pilot में किस आयु वर्ग के युवाओं को शामिल किया गया था?
```

Expected: `21–24 वर्ष`, PDF page **2**. Aur verified options [PRESENTATION_QA.md](PRESENTATION_QA.md) mein hain.

### Step 8 — class ke baad safe shutdown (optional)

```powershell
.\scripts\native.ps1 stop
```

Yeh managed project services ko stop karega; PostgreSQL, personal Ollama, private DB aur uploaded originals delete nahi karega. Agar manually separate terminals mein services chalayi hain, us mode mein har terminal ke andar `Ctrl+C` use hota hai—dono run methods mix mat karo.

## Agar yeh bilkul fresh computer ho

Yeh kal ke same-laptop demo ke steps nahi hain. Fresh setup se pehle Python 3.12, Node.js 22.12+, PostgreSQL 18, Git aur official Ollama compatible runtime install/prepare karne padte hain; model downloads several GB ke ho sakte hain. Internet aur disk space chahiye.

### 1. Dependencies

Project root ke PowerShell terminal mein, sirf new checkout par:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock
npm.cmd --prefix frontend ci
```

`npm.cmd` PowerShell npm execution-policy issue se bachata hai.

### 2. Fresh PostgreSQL config aur schema

Sirf jab installation/database `.env` pehle se configured na ho:

```powershell
.\.venv\Scripts\python.exe backend\manage.py configure
```

PostgreSQL `postgres` admin password hidden prompt par type karo. Phir:

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini current
```

Expected schema head `0009_answer_feedback`.

### 3. Admin aur models prepare karo

First admin tabhi banana jab DB mein admin na ho; command identity aur password hidden prompt par poochega:

```powershell
.\.venv\Scripts\python.exe backend\manage.py bootstrap-admin
```

Model preparation explicit, one-time downloads hain:

```powershell
.\.venv\Scripts\python.exe backend\prepare_model.py
.\.venv\Scripts\python.exe backend\prepare_llm.py
```

`prepare_model.py` E5-small embedding model laata hai. `prepare_llm.py` official prepared Ollama runtime ke through pinned Qwen model aur tokenizer download/prepares karta hai (about 2.5 GB model plus tokenizer). Runtime location/version/pins setup docs mein check karo. Personal Ollama ko replace/uninstall mat karo.

### 4. Demo corpus ko import/index karo

Curated manifest ke official sources download/checksum verify:

```powershell
.\.venv\Scripts\python.exe backend\corpus.py --download
```

Fresh active admin/schema ready hone ke baad source metadata ke saath import:

```powershell
.\.venv\Scripts\python.exe backend\corpus.py --import
```

Import/processing jobs ke baad `native.ps1 start` se services chalao aur Admin/Search UI se extraction, rights/eligibility review aur indexing status verify karo. Sirf reviewed eligible source Ask mein use hota hai; PDF upload karna akela kaafi nahi.

## Troubleshooting quick checks

- **Browser `ERR_CONNECTION_REFUSED`:** frontend chalu nahi; root se `status`, phir `start`.
- **API `/health/ready` fail:** PostgreSQL service/config/migration ko check karo; existing `.env` delete/overwrite mat karo.
- **Ask says worker unavailable:** `native.ps1 status`; `rag` managed owner missing ho to `native.ps1 start` se missing service start karao; UI Retry.
- **Ask says insufficient evidence:** model ko prompt badal ke force mat karo. Source eligible/indexed hai ya nahi dekho; narrow fact question use karo. Ineligible sources ko answer ke roop mein present na karo.
- **Port busy / external owner:** process identify/owner check karo; duplicate API/index/RAG start mat karo.

## VS Code mein manual 5-terminal alternative

Recommended `native.ps1 start` use karo. Sirf jab manual terminal mode chahiye, exactly **five** VS Code terminals kholo, har ek project root par, aur commands ek-ek alag terminal mein chalao:

1. Terminal 1: ` .\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --no-proxy-headers --no-access-log`
2. Terminal 2: `npm.cmd --prefix frontend run dev`
3. Terminal 3: ` .\.venv\Scripts\python.exe backend\worker.py`
4. Terminal 4: ` .\.venv\Scripts\python.exe backend\index.py serve`
5. Terminal 5: ` .\.venv\Scripts\python.exe backend\rag.py`

The leading spaces above are just for readability—paste command without that first space. Wait for Uvicorn, Vite (`http://127.0.0.1:5173/`), index readiness and `Local RAG worker ready; one pending job; project Ollama 127.0.0.1:11435`. Keep each terminal open. Stop each with `Ctrl+C`. **Do not use manual terminals and managed `native.ps1` for the same services at the same time.**
