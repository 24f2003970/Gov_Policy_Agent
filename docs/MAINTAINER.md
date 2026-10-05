# Maintainer state

Updated 2026-10-06. Parts 1–6 are implemented. Next phase is Part 7; do not begin it automatically. The recurring beginner-explanation requirement is withdrawn; future work uses concise technical documentation.

## Continuation baseline

- Current schema: `0005_citations`; preserve configured databases, private `.env`, originals and existing administrator. No application reset or reprovisioning is required.
- Local environment: Windows 11/PowerShell, bundled Python 3.12.14 `.venv`, Node 24.12.0, PostgreSQL 18.6. CPU i5-13500HX, about 15.7 GiB usable RAM, RTX 4050 with 6141 MiB VRAM. Part 5 measured GPU offload with the pinned 4B Q4 model; see verification for timing/memory and Hindi limitations.
- Pre-Part-4 documentation cleanup: `cfa7006a849bdf056da5372c44d98f1d70f43c85`. Historical ingestion: `d59aaf9392ce492dcd95bd18406d4f9ee09219dc`; auth: `fedc1c43a38324795f1d61a7348c2274407006ff`; foundation: `e8a41e16ba7e1c3b298724a05930d5fd6aae7c9b`. Part 4: `0f987b8470c06ddf09f5fd4a65204634e9fcaf0f`. The Part 5 release is the commit introducing the local-answer implementation; use Git history for its hash.
- Setup commands have one home in [SETUP.md](SETUP.md); schema/security detail in [ARCHITECTURE.md](ARCHITECTURE.md), measured evidence in [VERIFICATION.md](VERIFICATION.md), proposal traceability in [requirement mapping](../REQUIREMENTS_MATRIX.md).

## Decisions to preserve

Use a local modular monolith, PostgreSQL and private immutable originals. Keep dependency locks and explicit migrations; backend lock is a resolved version lock, not a wheel-hash or cross-platform guarantee. Test database/role are separate and disposable; application data is not.

Auth uses server-authoritative roles/revocation, Argon2id, rotating opaque refresh sessions, memory-only access tokens, CSRF/exact-origin checks and durable throttling. Preserve hidden-input provisioning and first-admin-only bootstrap; no default credentials.

Ingestion uses raw streams, global checksum dedup, private generated storage keys, bounded child parsing, durable fenced jobs and atomic results. Preserve exact original/page/text provenance, unknown dates and explicit evidence-backed relationships. Newer documents do not automatically supersede old ones. Audited append-only eligibility reviews permit corrections without mutating original-version metadata; no hard-delete workflow exists.

Official origin, legal status and reuse permission are distinct. Of four real versions, one historical PIB text factsheet is eligible/indexed (nine passages); three original sources remain excluded. Expansion toward 10–20 documents across 3–5 schemes requires rights and extraction review. Proposal PDF is requirements material, never policy evidence; synthetic fixtures are test-only.

Keep pinned multilingual E5-small on CPU/two threads, normalized 384-dimensional cosine vectors, explicit query/passage prefixes and token profile `e5-token-v1:448:48`. Retain old provisional chunks and generation-scoped provenance. One Windows file-locked process owns model/Chroma; the API uses private loopback IPC. SQL gates every retrieval and generation activation. Changed reviews require rebuilding; archive/rejection takes effect immediately. No mixed revisions, automatic downloads or default Chroma embeddings. Reconcile does not garbage-collect historical collections. Current bounds: 100 versions, 20,000 passages, batch eight, three attempts, one runtime operation at a time.

## Remaining roadmap

| Part | Planned work |
| --- | --- |
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

Known gaps: OCR, table/encoding quality, wider corpus rights clearance, malware scanning, parser isolation/hard memory quotas, production HTTPS/security, CPU generation fallback, throughput and held-out retrieval evaluation. The 12-case development set was source-checked by the implementing agent; independent human review is pending. Ambiguous questions still return candidates; the 0.78 cutoff is not calibrated. Historical upstream TestClient deprecation remains. Update technical records with actual results when future work is authorized.

## Answer baseline to preserve

Qwen3 4B Instruct 2507 Q4_K_M through Ollama 0.17.1; exact pins in [model record](llm_model.json). Keep 4096 context/768 output/temperature 0/seed 28/non-thinking, single pending job, complete prompt-token counts, explicit failures and contained cancellation. Preserve exact excerpt handles, server-built final claims, source locks, private owned history and null trust. One historical PIB source remains the entire answer corpus; no rights/extraction status was relaxed. No further models or fine-tuning were used. English/Hindi development samples and implementing-agent manual review do not establish held-out accuracy; Hindi output limits/language errors remain. Part 6 adds exact SQL provenance, stable additive claim/citation records, final-language scope/value guards and a bounded same-Qwen support judge. Exact provenance and heuristic support remain separate from current applicability. No reassessment/backfill of Part 5 answers occurred; API history redacts answer/excerpts when current source/review/provenance access changes. Private snapshots remain unchanged. Only retained claims form a new answer; rejected candidates have controlled reasons rather than exposed policy prose.

Preserve `layered-qwen-v2`/`support-judge-v1`, 30-second judge deadline, 256-output-token reserve and no excerpt clipping. One production claim, at most one judge call per candidate; one original schema repair remains bounded. Conflicting annual amounts are checked only among selected same-scheme contexts; this is not an exhaustive corpus/legal conflict detector. Generation may omit Hindi qualifiers and conservatively abstain; do not relax guards to improve apparent coverage. The 35-case support devset was tuned/reviewed by the implementing agent; independent labels and held-out evaluation remain pending.

A pre-release Hindi recipient/DBT false accept under v1 was found in browser review; v2 guards reject the added development case. Preserve its recorded private v1 assessment, expose the method mismatch and do not silently backfill/reassess. See VERIFICATION for the full limitation and measured final results.
