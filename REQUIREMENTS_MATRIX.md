# Requirement mapping

Source: full local GOV-CS-028 proposal, 34 physical pages, read 2026-10-05. The PDF is ignored and not reproduced in this public repository. This matrix covers functional modules, objectives, quality controls, design choices and stated future scope; front matter and bibliography are reference material, not application features. **Planned** means no functionality delivered yet.

| Requirement / proposal location | Planned part | Current status and adaptation |
| --- | --- | --- |
| O1 grounded policy Q&A; pp.5,10,14 | 4–5 | Planned; curated official evidence only |
| O2 clause/claim-level citations; pp.14,21 | 6 | Planned; version, exact page and verbatim passage; section/clause only if actually present |
| O3 six-dimensional trust; pp.14,22,26 | 8 | Design documented; all components currently unavailable; experimental index |
| O4 Hindi/English; pp.14,18,29 | 4,7,9 | Planned; practical Hinglish added by user; badges are planned language labels |
| O5 hallucination <5%; p.14 | 11 | Aspirational; not measured or guaranteed |
| O6 Docker/cloud production; pp.14,30 | 12 | Local Compose planned; cloud outside free baseline; not production-ready now |
| S1 500 documents/10 ministries; p.14 | 3–4,11 | Adapted to 10–20 verified files/3–5 schemes first; current corpus zero |
| S2 retrieval P@5 ≥0.80; pp.14,30 | 11 | Aspirational; current retrieval unimplemented |
| S3 PDF, scanned PDF, HTML, text; pp.14–15,19 | 3,7 | Digital PDF/TXT first, OCR later, HTML scoped after baseline; DOCX deferred |
| S4 feedback improvement; pp.14,22 | 10 | Planned; manual review, no automatic training from user ratings |
| S5 admin corpus/system dashboard; pp.14,22 | 3,9–10 | Planned; durable statuses and real counts |
| S6 MLflow/model monitoring; pp.14,30 | 10–11 | Reproducible experiment records planned; MLflow optional only if useful |
| S7 research publication; pp.14,31 | 12 | Optional future research; no acceptance promise |
| User management/profile/guest-user-admin; p.19 | 2,9 | Planned; server-enforced roles, guest behavior to define in Part 2 |
| OAuth2/JWT/login/logout/refresh/brute-force limits; p.19 | 2,11 | Planned; review secure library/hash/token choices then |
| Admin drag/drop upload, formats/size/virus scan; p.19 | 3,9,11 | Planned; 50 MB proposed cap to review; disclose unavailable malware scanner |
| Scanned PDF detection/Tesseract eng+hin/300 DPI; pp.19–20 | 7 | Planned; bounded per-page OCR, measured quality and preserved page references |
| PDF text/headings/tables/metadata PyMuPDF; p.20 | 3 | Planned; uncertain extraction/dates flagged; tables handled explicitly |
| Clause-aware chunking, 512 tokens/50 overlap; p.20 | 3–4 | Planned; tokenizer/model limits and page mapping guide measured chunk sizes |
| SBERT+MuRIL, 768 dimensions; p.20 | 4 | One multilingual model first; dimension derived from selected revision |
| Vector CRUD/HNSW/filtering; pp.20–21 | 4 | Persistent Chroma planned, no Pinecone baseline |
| Top20 → rerank top5; HyDE; p.21 | 4,11 | Simple retrieval first; candidates/top-k/reranker only after evaluation |
| Ollama Mistral/Llama, temp0.1/context4096/streaming; p.21 | 5,9 | Replaceable benchmarked local model; context and generation limits measured |
| Claim extraction/cosine source mapping; p.21 | 6 | Citation support validation required; similarity cannot prove a claim |
| Personal dashboard/history/saved answers/trust timeline; p.22 | 2,9 | Schema design only; unavailable scores absent |
| Admin analytics/topics/P@5/feedback/error rates; p.22 | 10–11 | Actual persisted events and labeled evaluation only; feedback ≠ accuracy |
| Feedback ratings/comments/review flags; p.22 | 10 | Planned with ownership, privacy and moderation |
| PostgreSQL users/documents/chunks/queries/citations/trust/feedback; pp.23–27 | 2–10 | Initial relational design documented; migrations start Part 2 |
| Source versioning/amendments/supersession; pp.10,12 | 3–6 | Planned verified relationships; publication/ingestion/verification separate |
| Swagger/OpenAPI; p.15 | 1 | Implemented at /docs and /openapi.json |
| React/Tailwind/FastAPI layered architecture; pp.3,16–18 | 1 | Implemented starter, modular monolith; TypeScript/Vite added |
| Restricted CORS/config/errors/request IDs/health (user additions) | 1 | Implemented and tested; AI-free liveness, phase-aware readiness |
| Real browser connectivity/loading/error/retry (user additions) | 1 | Implemented; readiness endpoint checked, no fake answers/stats |
| Pinned dependencies/lockfiles/local setup (user additions) | 1 | requirements.lock and package-lock.json, PowerShell instructions |
| Source legitimacy/rights/provenance; pp.15,32 | 3,11 | Verify official source and rights; do not assume public availability grants unrestricted reuse |
| Security/JWT/TLS/rate limiting; pp.4,19,30 | 2,11–12 | Local loopback HTTP now; auth/rate limits later; TLS if exposed later |
| Resource profiling/performance/OWASP review; p.30 | 11 | Hardware inventory only now; no throughput claims |
| Reproducible test set/BLEU/ROUGE/BERTScore; pp.30–31 | 11 | Test set/quality metrics planned; prioritize evidence support and abstention |
| Full report/demo/video/viva and public code; pp.30–31 | 1,12 | Beginner foundation docs now; final report/demo later |
| Eight-month multi-person roadmap; pp.28–30 | 1–12 | Adapted to user-directed numbered parts, solo pace, no deadline |
| GPU/translation/OCR/vector-scale/copyright/team risks; pp.31–32 | 3–12 | Local CPU fallback, quality flags, measured expansion, documented handover |
| Additional Indian languages, mobile, voice; pp.15,32 | Beyond 12 | Deferred; no implementation in baseline |
| Live feeds, legal advisory, multimodal, federated hosting, fine-tuning; p.32 | Beyond 12 | Deferred; no training or legal advice in baseline |

## Cross-cutting acceptance rules

User input and retrieved instructions are untrusted data. Preserve original passages; generated translations must not masquerade as verbatim evidence. Ask for clarification for ambiguous scheme/jurisdiction/date questions. Abstain when no support exists. Maintain immutable source versions and verified supersession scope. Never fabricate publication dates, document counts, evaluation results or trust values. These controls remain design requirements for Parts 3–11; Part 1 does not claim RAG safety has been implemented.
