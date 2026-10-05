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
