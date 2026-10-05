# Maintainer state

Updated 2026-10-05. Parts 1–3 are complete; Part 4 has not started. This cleanup changes documentation only. The recurring beginner-explanation requirement is withdrawn; future work uses concise technical documentation.

## Continuation baseline

- Current schema: `0002_documents`; preserve configured databases, private `.env`, originals and existing administrator. No application reset or reprovisioning is required.
- Local environment: Windows 11/PowerShell, bundled Python 3.12.14 `.venv`, Node 24.12.0, PostgreSQL 18.6. CPU i5-13500HX, about 15.7 GiB usable RAM, RTX 4050 with 6141 MiB VRAM. GPU/model performance has not been measured.
- Latest implementation release: `d59aaf9392ce492dcd95bd18406d4f9ee09219dc`. Historical auth release: `fedc1c43a38324795f1d61a7348c2274407006ff`; foundation: `e8a41e16ba7e1c3b298724a05930d5fd6aae7c9b`.
- Setup commands have one home in [SETUP.md](SETUP.md); schema/security detail in [ARCHITECTURE.md](ARCHITECTURE.md), measured evidence in [VERIFICATION.md](VERIFICATION.md), proposal traceability in [requirement mapping](../REQUIREMENTS_MATRIX.md).

## Decisions to preserve

Use a local modular monolith, PostgreSQL and private immutable originals. Keep dependency locks and explicit migrations; backend lock is a resolved version lock, not a wheel-hash or cross-platform guarantee. Test database/role are separate and disposable; application data is not.

Auth uses server-authoritative roles/revocation, Argon2id, rotating opaque refresh sessions, memory-only access tokens, CSRF/exact-origin checks and durable throttling. Preserve hidden-input provisioning and first-admin-only bootstrap; no default credentials.

Ingestion uses raw streams, global checksum dedup, private generated storage keys, bounded child parsing, durable fenced jobs and atomic results. Preserve exact original/page/text provenance, unknown dates and explicit evidence-backed relationships. Newer documents do not automatically supersede old ones. No hard-delete/audited verification-correction workflow exists yet.

Official origin, legal status and reuse permission are distinct. The current three-source local-reference corpus is not eligible for retrieval. Expansion toward 10–20 documents across 3–5 schemes requires rights and extraction review. Proposal PDF is requirements material, never policy evidence; synthetic fixtures are test-only.

## Remaining roadmap

| Part | Planned work |
| --- | --- |
| 4 | One replaceable multilingual embedding model, persistent Chroma and measured retrieval |
| 5 | Benchmarked local Ollama generation, grounded context and abstention |
| 6 | Claim-level exact version/page/passage citations and support validation |
| 7 | Hindi/Hinglish checks and bounded OCR with page/quality provenance |
| 8 | Transparent experimental evidence-quality scoring |
| 9 | Chat/source/history/saved-answer frontend workflows |
| 10 | Feedback, genuine analytics and experiment records |
| 11 | Held-out evaluation, security review and resource profiling |
| 12 | Local Compose packaging, backup/restore and final project deliverables |

HTML remains after baseline and DOCX deferred. No paid API, fine-tuning or cloud baseline. Reranking, HyDE, translation frameworks and monitoring frameworks require measured need. Model selection must check license, language support and memory; never mix embedding revisions/dimensions. Start conservatively and benchmark before increasing model/context/batch sizes.

## Evaluation constraints

Measure retrieval P@k/recall, claim support, citation correctness, abstention, language quality, latency and RAM/VRAM using manually checked questions, including insufficient/conflicting evidence. Proposal targets P@5 ≥0.80, hallucination <5%, large corpus/publication and scalability are aspirations, not results. Similarity, BLEU/ROUGE/BERTScore and user feedback do not establish factual support.

Proposed score dimensions/weights are unvalidated: recency 20%, citation coverage 25%, semantic faithfulness 25%, consistency 15%, calibration 10%, feedback 5%. All are currently unavailable. Preserve missing values, formula version and coverage; do not invent components or silently reweight. Thresholds and calibration need evaluation.

Known gaps: OCR, table/encoding quality, rights clearance, malware scanning, parser isolation/memory/concurrency budgets, production HTTPS/security, multi-worker resource behavior and model evaluation. Historical upstream TestClient deprecation remains. Update technical records with actual results when future work is authorized.
