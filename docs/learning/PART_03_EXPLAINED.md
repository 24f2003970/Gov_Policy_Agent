# Part 3 samjho: document ko reliably upload, inspect aur process karna

## 1. Purpose aur previous part se difference

Part 1 ne working screen/API di. Part 2 ne accounts aur permissions di. Part 3 ne admin ko actual PDF/TXT sources safely store aur inspect karne ka workflow diya. File se text aur chunks nikalte hain, lekin **AI answer, embeddings, vector search, citations aur trust score abhi nahi bante**.

Library example: ab librarian book receive karta hai, uski edition/source details likhta hai, pages ko indexable text mein convert karta hai aur incomplete work clearly mark karta hai. Book receive hona aur uske har claim ko sach/legally current verify karna same cheez nahi.

## 2. Concepts ko basics se samjho

| Concept | Meaning | Everyday example |
| --- | --- | --- |
| Upload | Browser se file bytes API ko bhejna | Librarian ko book hand over karna |
| Bytes | File ka actual stored data | Book ki physical printed copy |
| PDF extraction | Digital PDF ke text layer ko read karna | Printed book se existing typed text copy karna |
| OCR | Image ke letters ko text mein recognize karna | Photo dekhkar words type karna; Part 7 mein aayega |
| Metadata | File ke baare mein details | Title, author, edition, publication date |
| Document | Ek logical source/book identity | Ek policy guideline ka name |
| Version | Us source ki specific immutable edition | Revised edition ko purani edition se separate rakhna |
| Immutable | Original bytes/source details casually overwrite nahi hote | Purani edition ko white-out karke change na karna |
| Checksum | Bytes se calculated SHA256 fingerprint | Do copies bilkul same hain ya nahi, test karna |
| Deduplication | Identical content ki duplicate processing avoid karna | Same book baar-baar catalog mein add na karna |
| Provenance | Source kahan se aaya aur kisne check kiya | Book ka publisher/source receipt |
| Offset/span | Text ka exact start/end position | Notebook mein character number se passage locate karna |
| Chunk | Source text ka smaller piece | Bade chapter ko overlapping reading cards mein divide karna |
| Ingestion | File receive se structured text/chunks tak processing | Book receive, catalog aur page indexing ka poora workflow |
| Job | Database mein saved processing task | Pending-work register mein entry |
| Worker | API se alag program jo pending jobs karta hai | Reception se separate indexing staff |
| Retry | Failed job ka bounded next attempt | Failed photocopy ko limit ke andar dobara karna |
| Lease/heartbeat | Temporary work ownership / “main abhi kaam kar raha hoon” update | Assigned task ka timed pass aur regular check-in |
| Transaction | Related DB changes all-or-nothing | Complete indexing save ho, ya incomplete batch rollback ho |
| Archive | Record retain karke normal processing/use se remove karna | Book ko archive shelf par rakhna, destroy nahi karna |

Checksum **authenticity certificate nahi**. Fake PDF ka bhi valid SHA256 hota hai. `.gov.in` source claim bhi automatically verified nahi. Exact title, issuer, origin aur rights inspect karne padte hain. Source-origin verification, reuse permission aur current policy validity separate issues hain.

## 3. User action se result tak actual flow

1. Existing admin privately login karta hai. Backend current role/session check karta hai.
2. Admin source file aur title/issuer/scheme/source URL/language fill karta hai. Unknown dates blank rehti hain. Reuse rights truthful select hote hain.
3. Browser raw file bytes send karta hai. Metadata encoded header mein hai, URL/access log mein nahi.
4. Backend JWT, admin role, Origin aur CSRF header verify karta hai **before consuming file stream**.
5. File generated temporary name par stream hoti hai. Actual received size counted hota hai; 50 MiB cross hote hi rejection/cleanup. Fake Content-Length ya MIME label help nahi karta.
6. Separate parser child actual PDF/TXT validate karta hai. Encrypted/repaired/broken PDF, invalid UTF-8, wrong extension, empty/over-limit file reject hoti hai.
7. SHA256 lookup exact duplicate detect karta hai. Same bytes/same metadata existing version return karte hain; conflicting metadata 409 hai.
8. Valid new bytes generated original filename se atomically publish hote hain. Document/version plus queued job transaction mein save hote hain. Upload provenance initially unverified hai.
9. Separate worker PostgreSQL queued job claim karta hai. One job at a time recommended hai.
10. Worker original checksum rechecks, then killable parser child start karta hai. Child exact page text/flags/spans produce karta hai; parent heartbeat aur bounded progress save karta hai.
11. One result transaction all extracted pages/chunks aur terminal status save karti hai. Failure mein partial completed results publish nahi hote.
12. Admin UI real saved state poll karke completed/partial/needs_ocr/failed dikhati hai. Original page/text/preview inspect kiye ja sakte hain.

API worker ke bina bhi login aur listing serve karti hai. Worker stop ho toh pending job **queued** rehti hai, pretend-completed nahi hoti.

## 4. Important files/folders ka connection

| Actual source | Kya karti hai |
| --- | --- |
| [document_models.py](../../backend/app/document_models.py) | Seven phase-specific relational tables |
| [documents.py](../../backend/app/documents.py) | Metadata schemas, stream upload, dedup, admin list/detail/status/inspection/archive/retry/download/provenance/relationships |
| [storage.py](../../backend/app/storage.py) | Private directories, safe generated keys, checksum, bounded validation-child command |
| [parser_child.py](../../backend/parser_child.py) | Real PyMuPDF/TXT parsing and bounded PNG page preview; no DB work |
| [extraction.py](../../backend/app/extraction.py) | Paragraph spans, conservative labels and deterministic provisional chunks |
| [ingestion.py](../../backend/app/ingestion.py) | Transactional claim, heartbeat, fencing, result commit, retry recovery and orphan reconciliation |
| [worker.py](../../backend/worker.py) | Separate Windows-friendly worker command, reconnect/poll loop |
| [corpus.py](../../backend/corpus.py) | Explicit curated download/import, checksum checks, existing admin reuse |
| [0002 migration](../../backend/migrations/versions/0002_documents_durable_document_ingestion.py) | Explicit tables/indexes/constraints and immutable-version trigger; no auth deletion |
| [DocumentAdmin.tsx](../../frontend/src/DocumentAdmin.tsx) | Real upload/list/status/inspection/preview/retry/archive UI |
| [auth.ts](../../frontend/src/auth.ts) | Existing memory JWT/refresh layer extended for binary responses/uploads |
| [corpus_manifest.json](../corpus_manifest.json) | Public reproducible source metadata/checksums, no source PDFs |
| [test_documents_postgres.py](../../tests/test_documents_postgres.py) | Synthetic isolated files + actual PostgreSQL/parser/process tests |

Default originals storage: `C:\Users\thiss\AppData\Local\GovPolicyAgent\data`, outside OneDrive. `originals` durable bytes rakhta hai; `temporary` short-lived upload/parser results. DB relative generated keys store karti hai. Ignored `runtime/corpus` download cache hai, durable original storage nahi. Storage move karte waqt DB backup aur directory copy dono preserve karo; sirf path change karne se files missing ho jayengi.

## 5. Tables, important functions aur endpoints

| Table | Purpose / important fields |
| --- | --- |
| `schemes` | Optional scheme grouping, UUID/name/timestamp |
| `documents` | Logical title, issuer, type, scheme FK, archive state |
| `document_versions` | Version number, checksum, size, original key/name, immutable metadata, nullable dates, uploader, ingestion time, verification decision/time, extraction revision/profile |
| `version_relationships` | Explicit verified amends/supersedes link, evidence URL, scope, verifier/time; no date-based automatic inference |
| `extracted_pages` | Physical PDF page number or TXT section, exact text, source start, paragraphs, method and quality flags |
| `chunks` | Version/page FK, ordinal, exact offsets/text, detected label, continued-clause flag/profile |
| `ingestion_jobs` | One job per version; state, attempt count, progress, lease owner/expiry/heartbeat, safe error and finish time |

UUID/fk/unique constraints prevent broken or duplicate relationships. Version source metadata updates are rejected by a PostgreSQL trigger. Verification/extraction revision fields can change under controlled code; original bytes have generated no-overwrite storage and integrity checks. Privileged manual DB/filesystem edits are outside this application guarantee.

All endpoints below require current admin. Prefix: `/admin/documents`. Mutation means changing state; POST/PATCH also require Origin+CSRF.

| Endpoint | Input | Result |
| --- | --- | --- |
| `POST /upload` | Binary body; filename; encoded X-Document-Metadata | 202 saved/existing version + job; 409 conflict; 413 size; 422 invalid contents |
| `GET /` | Page/limit | Bounded document list, latest version, real state |
| `GET /{document_id}` | UUID/page | Detail + latest 20 versions per API page |
| `GET /versions/{id}/status` | Version UUID | Persisted job/provenance/eligibility |
| `GET /versions/{id}/pages` | Version/page | Page/section summaries, physical numbering/flags |
| `GET /versions/{id}/pages/{ordinal}` | Ordinal/character offset | Exact 20,000-character text window + spans; total length provided |
| `GET /versions/{id}/chunks` | Version/page | 50 chunks per page with exact source offsets |
| `GET /versions/{id}/original` | Version | Integrity-checked protected unchanged PDF/TXT download |
| `GET /versions/{id}/preview/{ordinal}` | Version/physical PDF page | Protected bounded PNG rendered from original |
| `POST /versions/{id}/retry` | Failed version | Requeue only if attempts <3 and document active |
| `PATCH /{id}/archive` | Boolean archived | Archive/unarchive, preserve versions |
| `PATCH /versions/{id}/provenance` | Verified/rejected + evidence note | One-time manual decision/time; source claim isn't automatic |
| `POST/GET /versions/{id}/relationships` | Distinct verified versions, kind/evidence/scope / page | Record/inspect verified version links |

`persist_upload` connects storage publication, dedup and DB job creation. `validate_file` runs actual parser with deadline. `claim` assigns locked durable work; `heartbeat` extends owned lease; `finish` publishes coherently only while ownership is valid. `run_once` does one eligible job. `reconcile` only removes expired generated orphan files.

## 6. Extraction, chunks aur OCR-pending ko samjho

Digital PDF mein typed text layer ho sakti hai. `get_text('text', sort=False)` ka returned text exact store hota hai; physical page 1 ko page 1 hi bolte hain, printed document labels ko invent nahi karte. TXT ko fake PDF pages nahi milte: one text section plus character offsets hote hain. UTF-8 Unicode preserve hota hai.

Offset `[10,20)` ka meaning character 10 se start, character 20 se pehle end. Yeh Python Unicode character positions hain, byte offsets nahi. PDF spans exact extracted page text ke relative hain. TXT source_start plus local offsets original decoded text ko locate karte hain. Frontend ko independently byte/JavaScript UTF-16 offsets guess nahi karne chahiye.

Chunk profile **unicode-char-v1:1200:120** provisional hai: max 1,200 characters, 120-character overlap, newline boundary preference. Example: chunk A `[0,1200)`, B normally `[1080,2280)`; overlap context ko boundary par preserve karta hai. Newline adjustment se actual boundaries vary kar sakti hain. Entire source coverage retain hoti hai; no silent truncation. Large clauses/paragraphs split ho sakte hain and continued-clause metadata milti hai.

Tokenizer text ko model-sized units mein divide karta hai. Final embedding model/tokenizer selected nahi, isliye **characters ko embedding tokens nahi bolte**. Part 4 immutable stored text se appropriate tokenizer chunks regenerate karega. No model download now.

Low-text PDF page mein <30 stripped characters hon toh needs_ocr flag lagta hai. Yeh “definitely scanned” proof nahi; blank/decorative page bhi flag ho sakta hai. All pages low-text: needs_ocr; digital aur incomplete mixed: partial; all digital enough: completed. Digital successes preserve hote hain. Blank/empty scanned document fully processed nahi dikhaya jata.

Table columns, reading order, fonts aur encoding imperfect ho sakte hain. Quality flags limitations expose karte hain. Paragraph/heading detection regex heuristic hai; headings/clause IDs sirf detectable patterns par, otherwise null. This is extraction, legal interpretation nahi.

## 7. Reliability aur technology choices

PostgreSQL already available tha; persisted queue ke liye extra Redis/Celery service nahi chahiye. SQLAlchemy sync DB work thread workers mein rehta hai; separate lightweight worker API se independent hai. PyMuPDF 1.28.2 real digital PDF parsing/rendering karta hai. AGPL/commercial dual license hai: free use ko license obligations respect karni hain, proprietary redistribution separate review hai.

Two workers same job claim na karein: row lock + SKIP LOCKED. SKIP LOCKED means already assigned locked row ko wait karne ke bajay skip karna. Lease default 45 seconds; parent roughly one-second child wait cycle mein heartbeat deta hai. Kill ke baad heartbeat rukti hai, lease expires, restart recover karta hai. New owner token purane worker ka result reject karta hai: isse fencing kehte hain.

Maximum three total attempts. Failed jobs automatically endless retry nahi karte. Admin below-limit retry controls it. Parser result temporarily saved hota hai; all pages/chunks and status one transaction mein commit hote hain. 100% means this ingestion attempt finished, not official validity/AI correctness.

50 MiB file, 500 pages, 2,000,000 extracted characters, 30-second default parser and 60-second upload reading bounds hain. One parser per worker recommended. Child killable hai but OS sandbox/hard memory quota nahi; malicious native parser/resource attacks remain limitation. Virus scanner **unavailable**, scanning performed claim nahi.

## 8. Exact commands: kis folder aur terminal mein

All root commands:

```powershell
Set-Location 'C:\Users\thiss\OneDrive\Documents\ChatGPT\Gov_Policy_Agent'
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini current
```

Expected current: `0002_documents (head)`. Existing auth accounts retained; no configure/bootstrap/reset needed.

Terminal 1 (root), API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Terminal 2 (root then frontend):

```powershell
Set-Location frontend
npm.cmd run dev
```

Terminal 3 (root), worker:

```powershell
.\.venv\Scripts\python.exe backend\worker.py
```

Expected worker startup text; Ctrl+C stops it. One job or cleanup:

```powershell
.\.venv\Scripts\python.exe backend\worker.py --once
.\.venv\Scripts\python.exe backend\worker.py --reconcile
```

Cleanup grace: generated unreferenced original older than 24 hours, temporary artifact older than one hour. Known/reference files aren't deleted. Don't manually move originals while API/worker runs.

Explicit demo (root):

```powershell
.\.venv\Scripts\python.exe backend\corpus.py --download
.\.venv\Scripts\python.exe backend\corpus.py --import
```

Expected per-file validated/queued/existing message; no credentials printed. Changed official bytes/hash or network blocking fails safely and requires manifest review. Import existing active first admin reuse karta hai; new admin create nahi karta.

## 9. Feature kaise use/check karein

`http://127.0.0.1:5173/#admin` par login ke baad upload form milega. Select file, metadata fill, Upload and queue. Worker chalao. Document title click karo; job state, physical page list aur text visible honge. Source page choose karo; Load original preview chosen page ka PNG dikhata hai. Protected original download file bytes unchanged deta hai.

Retry failed job mein controlled retry hai; completed/partial/needs_ocr par deliberate 409 helpful message. Archive/unarchive controls reversible hain. Listing/status refresh karo; automatic polling stopped ho toh manual refresh use karo. Content React plain text/pre mein render hota hai, uploaded `<script>` HTML execute nahi hota. Preview image document scripts execute nahi karti.

New version checkbox selected document ke liye hai; same title/issuer/type/scheme retain karke genuinely different bytes upload karo. Relation records API se explicitly verified evidence/scope ke saath aate hain; newer date automatic supersession nahi.

## 10. Real corpus aur verification

Actual local corpus: **3 schemes, 3 PDF versions, 164 physical pages, 398 provisional chunks**. PM-KISAN 12 pages completed; PMJDY 40 and PMAY-U 2.0 112 pages partial because conservative low-text flags. Original covers and actual title/issuer inspected, hashes manifest se match. Unknown publication/effective dates null hain; cover revision/month ko guessed date mein convert nahi kiya.

Source provenance verified hai, but all three local-reference-only: reproduction permission obtained nahi. Isliye **zero versions future retrieval eligible**. PDFs/extracted corpus text Git mein nahi. Proposal never policy evidence; test fixtures synthetic and dedicated test storage/DB mein isolated hain.

Current executed backend suite: **56 passed**, real PostgreSQL plus real parser/worker-claim processes. Part 1/2 regressions included. Tests cover digital PDF/TXT, exact offsets/full coverage, duplicates/conflicts, malformed/encrypted/misleading/oversized inputs, mixed/scanned pages, admin/CSRF/access denial, original integrity/PNG cleanup, transactional rollback, leases/concurrent claim/stale fencing/attempt cap, real claim-process termination/recovery, archive/versions/provenance/relationships, orphan cleanup and auth-preserving migration. See [VERIFICATION.md](../VERIFICATION.md) for final release result and browser evidence; update this count if release changes it.

Application migration/repeated upgrade independently preserved existing 2 users/2 auth sessions exactly. TypeScript/build and pip check passed. Real admin browser upload of official PM-KISAN, worker processing and page inspection ran. Real protected PNG preview, completed-job retry 409, archive/unarchive aur final duplicate upload bhi browser mein verify hue. Repeated upload ne existing version/job reuse kiya; synthetic tests in checks ka substitute nahi hain.

Not verified: public deployment, malware scanning, OCR accuracy, table reconstruction accuracy, embedding/RAG quality, throughput/memory benchmarks, multiple-worker resource behavior. Existing upstream TestClient deprecation warning remains. No required check is called passing solely because code exists.

## 11. Common errors aur simple fixes

| Error/state | Meaning / fix |
| --- | --- |
| Queued | Worker isn't processing yet; start separate worker, check DB/schema/archive |
| Processing after worker killed | Lease recovery needs expiry/restart; original/job data retained |
| Failed | Read sanitized error code; fix original/setup issue, retry if attempts <3 |
| needs_ocr/partial | Digital text incomplete; inspect original, OCR deferred, don't mark fully ready |
| 409 metadata conflict | Same bytes already cataloged differently; inspect original existing metadata |
| 422 encrypted/malformed | Use legitimate digital unencrypted supported PDF; no password bypass is implemented |
| 413 | Actual received file exceeds 50 MiB, regardless of claimed length |
| Preview/inspection failed | Refresh status/select version again; re-login if expired; verify original integrity |
| 401/403 | Missing session vs missing admin/CSRF permission; preserve 127.0.0.1 origin |
| Ready 503 | PostgreSQL/schema/config unavailable; run explicit upgrade, inspect service |
| Missing original after move | Restore matching full storage backup; changing GOV_DATA_DIR alone cannot move bytes |

## 12. Beginner viva

1. **Upload aur ingestion same hain?** Upload bytes receive karta hai; ingestion validation/text/chunks/status workflow hai.
2. **Checksum kyun?** Byte identity, duplicate detection aur integrity checks ke liye; authenticity proof nahi.
3. **Document/version difference?** Logical policy identity vs its specific preserved edition.
4. **Provenance kyun?** Source origin aur manual checks traceable rakhne ke liye.
5. **Worker separate kyun?** Parsing fail/stop hone par login/API independent rehte hain.
6. **Durable job kya hai?** PostgreSQL task record jo process restart ke baad bhi rehta hai.
7. **Lease/heartbeat kyun?** Killed worker ka task detect aur safely reclaim karne ke liye.
8. **Chunk overlap kyun?** Passage boundary ke context loss ko reduce karta hai.
9. **Scanned PDF completed kyun nahi?** Text layer incomplete hai; OCR abhi implemented nahi.
10. **Source verified but retrieval eligible false kyun?** Complete extraction, reuse permission aur active state bhi required hain; retrieval itself future feature hai.

## 13. Bolkar explain karne ka short version

“Part 3 mein admin-only reliable document ingestion banaya. PDF/TXT originals generated private names se preserve hote hain. PostgreSQL document versions, provenance, pages, chunks aur durable jobs save karta hai. Separate worker lease aur heartbeat se processing recover karta hai; result transaction incomplete output publish nahi hone deti. Exact page numbers/text offsets inspection ko traceable banate hain. Scanned pages OCR-pending hain, source verification aur reuse rights separate hain. Is part mein embeddings ya AI answers nahi hain.”
