# Decisions and significant proposal adaptations

Recorded 2026-10-05, after reading all 34 physical PDF pages. Page numbers below refer to actual PDF pages; its table-of-contents/chapter numbering is inconsistent. The proposal is a starting reference. User constraints govern implementation.

| ID | Decision | Proposal reference and reason |
| --- | --- | --- |
| D01 | One modular FastAPI monolith with React frontend | pp.16–18 describe layers and same-process calls. Avoid unnecessary service/network complexity on one laptop. |
| D02 | Local PostgreSQL + persistent Chroma + original file storage later | pp.4,21,23 suggest Pinecone/cloud too. Free local baseline avoids hosted dependency and vendor lock-in. |
| D03 | Begin with 10–20 documents across 3–5 schemes | pp.14,28–31 aspire to 500 documents/10 ministries. Curated evidence quality and measured resources come first. |
| D04 | One multilingual Sentence-Transformers model initially | p.20 proposes SBERT plus MuRIL. Multiple embedding spaces add compatibility and memory costs; model revision remains replaceable. |
| D05 | Local Ollama model chosen by laptop benchmarks | pp.15,21,31 assume cluster/7B–8B or hosted fallback. Start smaller; no paid or remote inference baseline. |
| D06 | Native multilingual retrieval first; optional local normalization later | pp.18,29 propose translation and Google Translate API. No paid translation dependency; preserve original question and source text. |
| D07 | Citation similarity is a candidate signal only | p.21 uses cosine similarity. Exact quotations, version/page alignment and claim support checks are required; unrelated similar wording must not count as evidence. |
| D08 | Trust is an experimental evidence-quality index | p.22 six dimensions/weights preserved as research design, not validated confidence. Missing/calibration components remain unavailable; thresholds/weights are unvalidated hypotheses. |
| D09 | Recency must respect verified legal status | pp.12,22 favor recent documents. Keep publication/ingestion/verification dates separate; amendments need explicit verified relationships. |
| D10 | Durable ingestion jobs instead of fragile fire-and-forget | p.19 async ingestion expanded to persisted status, idempotency and retries in Part 3; no worker framework added now. |
| D11 | PDF/TXT first, OCR in Part 7; HTML after baseline, DOCX deferred | pp.15,19 list inconsistent formats. Focus on page-verifiable sources. Track HTML section anchors separately; do not invent page numbers. Virus scanning must be explicit if unavailable. |
| D12 | No forced reranker, HyDE, LangChain, Axios or monitoring stack | pp.3–4,21,30 propose them. Native fetch and direct interfaces suffice now; add reranking/other frameworks only after a measured benefit. No automatic query expansion baseline. |
| D13 | Authentication specifics reviewed in Part 2 | p.19 JWT/bcrypt/token lifetimes are proposals. Choose maintained libraries and secure hashing/session lifecycle with current docs at implementation; do not install auth now. |
| D14 | Local Docker Compose final packaging; cloud optional outside baseline | pp.13,30–31 assume AWS/GCP/public deployment. User requests free-only local reproducibility. Docker is not a Part 1 readiness dependency. |
| D15 | Measured evaluation, no promised metrics/publication/scalability | pp.8,14,30–31 claim millions of users, ≥0.80 P@5, <5% hallucination, paper acceptance. These are unverified aspirations, not delivered results. Unverified survey/novelty claims from pp.8–11 are not repeated as facts. |
| D16 | Proposal and source files stay outside public Git | Treat proposal as requirements only. Verify official sources and rights later rather than adopting p.15's blanket copyright assumption. |
| D17 | Fully pinned tested dependencies | npm package-lock includes integrity; backend requirements.lock pins the full resolved set for Python 3.12/Windows. Starlette 0.52.1 retains the documented httpx testing generation; resolver initially selected 1.7 with a migration warning. Upgrades require compatibility tests. |

## Part 2 decisions (2026-10-05)

- D18: Native PostgreSQL 18/current minor, dedicated gov_app/gov_policy plus isolated gov_test/gov_policy_test; no Docker prerequisite. Verify service/binaries before claiming installation.
- D19: Sync SQLAlchemy 2 + psycopg 3, explicit Alembic migrations; FastAPI sync endpoints move blocking DB/password work to worker threads. Preserve requirements.in/lock workflow.
- D20: Argon2id via pwdlib and HS256 PyJWT with required claims; 10-minute access and seven-day absolute refresh defaults. Passwords 12–128 characters, never truncated.
- D21: Server-authoritative session revocation/user status/roles on every protected access; no roles trusted from submitted signup data or stale JWT payloads.
- D22: HttpOnly host-only Strict /auth refresh cookie, memory-only access token, verified Origin + CSRF header, credentialed 127.0.0.1 CORS; production Secure/HTTPS mandatory.
- D23: Transactional row-locked refresh rotation; consumed-token reuse revokes the session. At most 256 consumed digests per session. Web Locks serialize same-origin browser tabs; unsupported browsers may need login after a rotation race. No grace window that silently accepts replay.
- D24: Persistent bounded fixed-window throttle, HMAC account/IP keys, five account attempts/15 minutes by default; Uvicorn proxy headers disabled. All login attempts count and limits expire, avoiding permanent locks.
- D25: Hidden-input local provisioning/admin CLI; generated per-install credentials, no default admin, only first admin bootstrap. Hash routes avoid an unnecessary frontend routing dependency.
- D26: Real PostgreSQL migrations/auth tests only. Required DB tests fail when prerequisites are missing; no SQLite/mocked completion. Frontend/backend verification and publication remain gated on actual results.

## Part 3 decisions (2026-10-05)

- D27: Seven document/provenance/derived-text/job tables only; explicit 0002_documents migration preserves auth. Source version snapshot protected by PostgreSQL immutability trigger, no application hard-delete endpoint.
- D28: Raw binary streaming uploads, authenticated before reading; metadata in encoded header, not URL logs. Enforce 50 MiB on actual stream, 60-second read deadline, safe generated storage names, actual parser validation.
- D29: Durable originals default to LocalAppData/GovPolicyAgent/data outside OneDrive; runtime download cache ignored. Atomic no-overwrite publication + DB job transaction, explicit grace-period orphan reconcile and paired storage/DB backups.
- D30: PyMuPDF 1.28.2 digital PDFs and exact UTF-8 TXT. Killable parser children, wall/page/text/output bounds; no claim of OS sandbox, hard memory quota or virus scan. Respect AGPL/commercial licensing; no new multipart dependency.
- D31: Preserve exact physical PDF pages/text and TXT spans. Provisional 1200-character/120-overlap profile; heuristic detected labels, continued-clause flag; no embedding tokenizer/model yet. Low-text pages conservatively OCR-pending; mixed PDFs partial, never silently ready.
- D32: Separate PostgreSQL worker, transactional SKIP LOCKED claims, heartbeat/lease ownership fencing, at most three attempts, coherent result transaction. Failed below-limit admin retry only; no in-memory queue or endless automatic retry.
- D33: SHA256 dedup scope is entire corpus. Same bytes/same metadata reuse version/job; conflicts return 409. New byte editions attach to selected logical document; amendments/supersession require distinct verified versions and explicit evidence/scope, never newer-date inference.
- D34: Authenticated bounded PNG original-page preview plus original byte download; React plain-text rendering, no uploaded HTML/scripts embedded. Real persisted status polling capped/cleaned up; API health does not require worker/AI.
- D35: Three real official-origin PDFs, 164 pages, local-reference-only. Source authenticity observations separate from reproduction permissions; no source PDF/extracted corpus text in Git, no eligible retrieval corpus until rights cleared. Synthetic tests isolated from real corpus.
- D36: Every numbered part includes its own beginner Hinglish learning guide and README link in the verified phase commit; Parts 1/2 documented retroactively without rebuilding.

## Six proposed trust dimensions

| Dimension | Proposal weight (unvalidated) | Planned interpretation / availability |
| --- | --- | --- |
| Source recency | 20% | Status-aware age/freshness signal; unknown dates/status stay unavailable; old does not imply invalid |
| Citation coverage | 25% | Fraction of factual claims with verified supporting passages; presence of citation links alone is insufficient |
| Semantic faithfulness | 25% | Supported meaning, numbers, conditions and negation; similarity alone is insufficient |
| Cross-document consistency | 15% | Compare scope and versions; conflicts/one-source coverage explicitly reported |
| Model calibration | 10% | Unavailable until a meaningful held-out calibration method has been evaluated; token confidence is not calibrated truth |
| User feedback history | 5% | Unavailable with insufficient feedback; subject to bias/manipulation and never proof of correctness |

Do not fill missing components with fabricated values or silently reweight into a full score. Part 8 must define whether a partial index is defensible, expose denominator/coverage, version the formula and evaluate it. All six are currently unavailable. Green/yellow/red thresholds from the proposal are not adopted as validated guarantees.
