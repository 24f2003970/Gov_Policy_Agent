# Incremental project plan

Parts 1, 2 and 3 are authorized through their respective prompts. Current scope is Part 3 only. Start each later part only after its prompt; update progress, decisions, requirement mapping and verification after each part. No fixed deadline is assumed.

Required learning workflow for every future numbered part: create docs/learning/PART_XX_EXPLAINED.md in beginner Hinglish, explaining actual concepts/flow/files/functions/endpoints/tables/choices/commands/usage/tests/errors/viva and a spoken summary. Link actual sources relatively, distinguish implemented/planned/deferred features, update if implementation changes, and include it with README Learning Guide link in the same verified phase commit/push. Parts 1/2 guides document existing behavior without rebuilding those parts.

| Part | Scope | Completion evidence |
| --- | --- | --- |
| 1 | Foundation and environment | Health tests, frontend type checking/build, actual browser connection, reviewed commit/push |
| 2 | Database, authentication and roles | Real PostgreSQL migration from empty + repeated upgrade, secure auth, browser flows, process persistence, role enforcement |
| 3 | Document upload, extraction and durable ingestion | Admin upload, validated originals, page text, retryable persisted jobs, source manifest |
| 4 | Multilingual embeddings and retrieval | One replaceable Sentence-Transformers model, persistent Chroma, measured retrieval over verified corpus |
| 5 | Local LLM and grounded RAG | Benchmarked Ollama model, context-only answers, clarification/abstention, resource/latency evidence |
| 6 | Claim-level citations and evidence verification | Exact version/page/verbatim passages; unsupported claims blocked or flagged; similarity is not proof |
| 7 | Hindi/Hinglish and scanned-PDF OCR | Cross-language and mixed-script tests; Tesseract eng/hin; OCR quality flags and page alignment |
| 8 | Transparent trust/evidence-quality scoring | All six design dimensions, available-component breakdown, explicit missing values and limitations |
| 9 | Complete frontend and admin workflows | Chat/streaming where feasible, citations, source inspection, roles, history, saved answers and ingestion status |
| 10 | Feedback, analytics and monitoring | Persisted feedback, genuine event aggregations, latency/errors, experiment records |
| 11 | Evaluation, security and optimization | Reproducible held-out bilingual/Hinglish tests, citations/abstention checks, security review, resource profiles |
| 12 | Docker packaging, final demo and viva documentation | Local Compose startup, persistent volumes, backup/restore instructions, honest demo and final report |

## Corpus and evaluation strategy

Part 3 starts with 3 inspected official-origin PDFs across 3 schemes, 164 physical pages, kept as local references only; reproduction permissions are not obtained. Further expansion toward 10–20 documents requires rights/extraction review. Keep source URL, issuer, checksum, unknown dates, ingestion and manual verification time separately. Expand only after retrieval, source coverage and laptop resource usage work.

Use explicit amendment/supersession relationships supported by source evidence, with scope and effective dates where available. Missing evidence remains unknown; a newer file does not automatically override an older one.

Start evaluation with a small manually checked set, including insufficient-evidence and conflicting-version questions. Record retrieval P@k/recall, claim support, citation correctness, abstention, language quality and latency/RAM/VRAM. Expand the set later; the proposal's 200+ items, P@5 ≥0.80 and hallucination <5% are aspirations. BLEU/ROUGE/BERTScore may supplement evaluation but do not establish factual support. Feedback is not ground-truth accuracy.

## Hardware-aware model selection

Measured laptop: i5-13500HX, about 15.7 GiB usable RAM, RTX 4050 with 6141 MiB VRAM. Part 1 downloads no models. In Part 4 choose one multilingual embedding model after comparing quality, license, size and RAM. Use one collection per model revision/dimension; never mix embedding spaces. Batch conservatively and preserve model/chunking revisions for reproducibility.

In Part 5 benchmark small quantized local instruction models first (roughly 1.5B–4B candidates), then try a 7B-class candidate only if memory allows. This is a size strategy, not a specific model recommendation. Verify current model licenses, Hindi support and Ollama compatibility then. Measure Hindi/English/Hinglish quality, groundedness, first-token latency, tokens/sec, peak RAM/VRAM and available context while the frontend/DB run. Keep one inference request at a time initially, bound context/output, and retain a CPU fallback. No fine-tuning, paid API or GPU server is required. No model has been selected or benchmarked yet.
