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
| S1 500 documents/10 ministries; p.14 | 3–4,11 | Adapted to 10–20 verified files/3–5 schemes first; Part 3 real local corpus: 3 official-origin PDFs/3 schemes/164 pages; all local-reference-only |
| S2 retrieval P@5 ≥0.80; pp.14,30 | 11 | Aspirational; current retrieval unimplemented |
| S3 PDF, scanned PDF, HTML, text; pp.14–15,19 | 3,7 | Part 3 digital PDF/UTF-8 TXT implemented; scanned/mixed quality flags delivered, OCR/HTML/DOCX deferred |
| S4 feedback improvement; pp.14,22 | 10 | Planned; manual review, no automatic training from user ratings |
| S5 admin corpus/system dashboard; pp.14,22 | 3,9–10 | Part 3 upload/list/status/page inspection/preview/retry/archive delivered; wider analytics deferred |
| S6 MLflow/model monitoring; pp.14,30 | 10–11 | Reproducible experiment records planned; MLflow optional only if useful |
| S7 research publication; pp.14,31 | 12 | Optional future research; no acceptance promise |
| User management/profile/guest-user-admin; p.19 | 2,9 | Part 2 verified with real PostgreSQL and browser: user/admin, protected language profile; guest access limited to health/public registration/login |
| OAuth2/JWT/login/logout/refresh/brute-force limits; p.19 | 2,11 | Part 2 verified: Argon2id, JWT bearer (no third-party OAuth login), rotating/revocable cookie sessions, persistent throttling |
| Admin drag/drop upload, formats/size/virus scan; p.19 | 3,9,11 | Part 3 native file selector, actual stream 50 MiB cap, content validation and private storage; virus scanning unavailable |
| Scanned PDF detection/Tesseract eng+hin/300 DPI; pp.19–20 | 7 | Part 3 conservative low-text detection and needs_ocr/partial states; Tesseract/OCR deferred |
| PDF text/headings/tables/metadata PyMuPDF; p.20 | 3 | Part 3 PyMuPDF exact physical-page text/spans; unknown dates null; heuristic headings, table layout not guaranteed |
| Clause-aware chunking, 512 tokens/50 overlap; p.20 | 3–4 | Part 3 replaceable provisional 1200 Unicode characters/120 overlap with page offsets and continuation flags; tokenizer-aware tuning deferred |
| SBERT+MuRIL, 768 dimensions; p.20 | 4 | One multilingual model first; dimension derived from selected revision |
| Vector CRUD/HNSW/filtering; pp.20–21 | 4 | Persistent Chroma planned, no Pinecone baseline |
| Top20 → rerank top5; HyDE; p.21 | 4,11 | Simple retrieval first; candidates/top-k/reranker only after evaluation |
| Ollama Mistral/Llama, temp0.1/context4096/streaming; p.21 | 5,9 | Replaceable benchmarked local model; context and generation limits measured |
| Claim extraction/cosine source mapping; p.21 | 6 | Citation support validation required; similarity cannot prove a claim |
| Personal dashboard/history/saved answers/trust timeline; p.22 | 2,9 | Schema design only; unavailable scores absent |
| Admin analytics/topics/P@5/feedback/error rates; p.22 | 10–11 | Actual persisted events and labeled evaluation only; feedback ≠ accuracy |
| Feedback ratings/comments/review flags; p.22 | 10 | Planned with ownership, privacy and moderation |
| PostgreSQL users/documents/chunks/queries/citations/trust/feedback; pp.23–27 | 2–10 | Parts 2/3 auth plus seven document/provenance/page/chunk/job tables verified against PostgreSQL 18.6; queries/citations/trust/feedback remain planned |
| Source versioning/amendments/supersession; pp.10,12 | 3–6 | Part 3 immutable versions and explicitly verified relationship APIs; legal dates separate from ingestion/verification, no automatic supersession |
| Swagger/OpenAPI; p.15 | 1 | Implemented at /docs and /openapi.json |
| React/Tailwind/FastAPI layered architecture; pp.3,16–18 | 1 | Implemented starter, modular monolith; TypeScript/Vite added |
| Restricted CORS/config/errors/request IDs/health (user additions) | 1–2 | Foundation retained; Part 2 credentialed CORS, DB/schema readiness and sanitized 503 added; AI-free liveness |
| Real browser connectivity/loading/error/retry (user additions) | 1 | Implemented; readiness endpoint checked, no fake answers/stats |
| Pinned dependencies/lockfiles/local setup (user additions) | 1 | requirements.lock and package-lock.json, PowerShell instructions |
| Source legitimacy/rights/provenance; pp.15,32 | 3,11 | Part 3 official origins/title/issuer/hash checked for three PDFs; permission not obtained, local reference only and zero retrieval-eligible versions |
| Security/JWT/TLS/rate limiting; pp.4,19,30 | 2,11–12 | Local loopback HTTP, JWT/cookie auth and durable throttling verified in Part 2; public TLS/security review remain later |
| Resource profiling/performance/OWASP review; p.30 | 11 | Hardware inventory only now; no throughput claims |
| Reproducible test set/BLEU/ROUGE/BERTScore; pp.30–31 | 11 | Test set/quality metrics planned; prioritize evidence support and abstention |
| Full report/demo/video/viva and public code; pp.30–31 | 12 | Final college deliverables remain planned; current repository keeps technical setup, source disclosures and verification |
| Eight-month multi-person roadmap; pp.28–30 | 1–12 | Adapted to user-directed numbered parts, solo pace, no deadline |
| GPU/translation/OCR/vector-scale/copyright/team risks; pp.31–32 | 3–12 | Local CPU fallback, quality flags, measured expansion, documented handover |
| Additional Indian languages, mobile, voice; pp.15,32 | Beyond 12 | Deferred; no implementation in baseline |
| Live feeds, legal advisory, multimodal, federated hosting, fine-tuning; p.32 | Beyond 12 | Deferred; no training or legal advice in baseline |

## Cross-cutting acceptance rules

User input and retrieved instructions are untrusted data. Future answering must preserve original passages, label translations, clarify ambiguous scheme/jurisdiction/date questions and abstain without support. Immutable source versions and explicit verified relationships are implemented; retrieval/answer safeguards remain planned. Publication dates, counts, evaluation results and trust values must remain evidence-based. See [maintainer state](docs/MAINTAINER.md) for continuation decisions.
