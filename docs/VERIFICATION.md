# Recorded verification

Executed 2026-10-05 on Windows 11/PowerShell 7.6.5, Python 3.12.14, Node 24.12.0/npm 11.6.2 and PostgreSQL 18.6. Earlier phase rows retain historical results; the Part 5 row records the current implementation run.

| Release | Backend | Other checks |
| --- | --- | --- |
| Foundation (Part 1) | 14 passed; clean lock install repeated | npm ci, TypeScript/build, browser connected/disconnected/recovered, mobile/desktop review |
| Authentication (Part 2) | 32 passed in 7.44s, including 16 real PostgreSQL cases | pip check, TypeScript/build, actual browser account/role/session flows |
| Ingestion (Part 3) | 56 passed in 22.84s, real PostgreSQL and parser/claim processes | pip check, TypeScript/build (33 modules), admin upload/inspection/preview/retry/archive |
| Retrieval (Part 4) | 65 passed in 64.06s, including nine real-model/vector/PostgreSQL retrieval cases | pip check, TypeScript/build (34 modules), offline real-source evaluation and browser Search |
| Local answers (Part 5) | 84 passed in 90.41s; final prompt/schema follow-up 16 passed in 0.88s | pip check, TypeScript/build (35 modules), real GPU inference and protected browser Ask/history |

One upstream Starlette/anyio BlockingPortal deprecation warning remained. Final ingestion tests used a new workspace temporary directory after old Windows pytest temp/cache permission failures. Reproducible commands and the temporary-directory workaround are in [SETUP.md](SETUP.md).

## Database and authentication evidence

PostgreSQL binaries/service and 127.0.0.1/::1-only listeners verified. Application/test connections used separate roles without superuser, database/role-creation or replication privileges. Empty and repeated migrations were tested in the dedicated test DB. Application upgrade to `0002_documents` and repeated upgrade preserved two existing users/two sessions exactly, including identity/hash/role fields; application tables were not reset.

Auth tests covered normalization, duplicates, Argon2id, token claim/algorithm/signature validation, live roles/status, row-locked rotation/replay/revocation, concurrency, cookies/CSRF, durable throttle, missing schema and unreachable DB. Browser checks covered registration, wrong-password error, login, language update, reload restoration, logout, normal-user admin denial and private admin access. Session restoration survived an actual API process restart.

## Ingestion evidence

Tests covered exact PDF/TXT offsets and full chunk coverage; duplicates/conflicts; invalid/encrypted/misleading/binary/path inputs; actual-stream size enforcement; page/text/parser-time bounds; scanned/mixed states; role/CSRF denial; original integrity/PNG cleanup; derived-insert rollback; concurrent claims, heartbeat/lease expiry/stale fencing/attempt caps; retry/archive/verified relationships/immutability and orphan cleanup.

Size enforcement was exercised with a lowered configured limit, not a 51 MiB browser upload. A real process was terminated after persisting a worker claim, then recovered after lease expiry by a new invocation; this was not a separate manual whole-worker crash demonstration.

Browser: uploaded official PM-KISAN through native file selection, separate worker processed it, all 12 physical pages listed, text inspected, protected PNG rendered and original download available. Completed retry returned 409. Archive/unarchive restored active state. Final duplicate upload reused the existing version/job and kept document count at three. A transient inspection fetch error was shown and recovered by reselection.

Measured corpus snapshot: three schemes/documents/versions, 164 pages, 398 chunks, one completed/two partial jobs, six low-text pages and three source-verification records. All local-reference-only; zero retrieval eligible. Repeated import reused existing records. Manifest hashes and original covers/title/issuer checked.

## Limits of evidence

Parts 1–3 did not evaluate generated-answer quality or GPU inference; Part 5 evidence is below. OCR, table reconstruction, throughput, multi-worker resource, public deployment and production-security evaluation remain pending. Malware scanning, OS parser sandbox and hard memory quota are unavailable. Health snapshot and transient recovery checks do not prove continuous monitoring or all timeout paths. Origin checks do not prove permission to reproduce sources.

Implementation releases were reviewed for ignored/private artifacts and pushed without force; commit identifiers are in [maintainer state](MAINTAINER.md). The preceding documentation cleanup checked links/commands/whitespace and documentation-only scope without changing historical measurements.

## Part 4 retrieval evidence

Additive application migration to `0003_retrieval` and repeated upgrade preserved the pre-existing users/sessions and source versions/pages/chunks by exact in-memory comparison; no application reset/reprovisioning. A fourth, seven-page PIB factsheet was then intentionally imported and fully extracted. The original three rights statuses and partial states were preserved. Final corpus: four documents/versions across three schemes, 171 extracted physical pages, one eligible/indexed version and three excluded. Active token-aware passages/vectors: nine, with exact set reconciliation reporting zero missing/zero orphan IDs. The 410 retained provisional chunks are a different profile, not additional retrieval evidence.

Real prepared E5 tensors, tokenizer and persistent Chroma were used in retrieval tests; no dummy encoder substituted for smoke retrieval. Tests covered normalized 384-dimensional Hindi/English vectors, token rejection/no truncation, complete exact-span chunk coverage, persisted vectors read by a separate process, idempotent upsert, model/revision/collection mismatch, filters/date unknowns, empty corpus, immediate archive/rights rejection, partial and explicit supersession exclusion, missing/orphan vector reconciliation, normal-user inspection/admin denial and internal-service authentication. A child process was terminated after a real SQL index claim; lease expiry enabled recovery, and a second Windows process could not acquire the owner lock. Injected batch failure was a test double specifically for failure handling; all successful builds/queries used the real encoder. Failed new generations kept the prior ready index; stale owners could not publish.

Browser checks used the actual protected Search API: Hindi annual-support query returned exact physical page 2 with source title/issuer/URL, IDs, historical scope and labeled cosine values; extracted page text inspection succeeded. Stopping the real index process produced a visible sanitized unavailable-service error. Persistence and recovery were checked after restarting the service. Loading and empty-result states were observed. Backend tests cover normal-user/admin boundaries; this Search browser journey used the existing private admin session. No private credentials were exposed.

### Small real-source development set

[Development set](retrieval_devset.json): twelve questions, including four grounded English/Hindi pairs, two ambiguous and two out-of-corpus cases. Questions/gold anchors were checked against all seven physical pages by the implementing agent. Independent human review is pending; this is not the final held-out benchmark. Gold document is identified by manifest checksum; the runner resolves its actual SQL version/page and exact anchor span before scoring.

Metric: gold-span hit@5, denominator four grounded questions per language. A hit requires the exact source version/page and an excerpt containing the full checked anchor span. No passage-by-passage precision labels exist, so **P@5 is not reported**. Both languages achieved 4/4 hits on this single-source set; no proposal accuracy target is established.

| Topic / gold physical page | English gold rank | Hindi gold rank |
| --- | --- | --- |
| Annual support / 2 | 1 | 1 |
| Crop inputs and moneylenders / 3 | 2 | 4 |
| Face authentication without OTP/fingerprint / 4 | 1 | 1 |
| EKstep/Bhashini chatbot / 5 | 1 | 1 |

The objectives query ranked a broad page-7 conclusion first in both languages; Hindi placed the precise page-3 anchor lower. Two ambiguous entitlement questions returned five candidate passages each, without an entitlement decision. Two Neptune questions returned empty at the heuristic 0.78 cutoff. These cases do not calibrate general ambiguity/abstention or establish claim correctness.

Final read-only CPU run after fresh SQL rechecks: grounded English median total 106.10 ms, Hindi 93.03 ms; all eight positive totals ranged 74.52–199.47 ms. The first query was 199.47 ms (embedding 63.63 ms). Runtime/model/Chroma initialization together took 13.068 seconds; process working set 777.1 MiB, peak 777.2 MiB, two Torch threads. Totals include model/vector/SQL checks, exclude HTTP/browser rendering, and describe sequential small-corpus queries on this laptop. Earlier cold browser Hindi query took 541.29 ms server total; latency varies with startup/system load. CPU-only Torch was retained; GPU memory/latency is unmeasured and no CUDA feasibility claim is made.

Commands are centralized in [SETUP.md](SETUP.md). Measured JSON output remains ignored under runtime rather than redistributing corpus text. Dependency compatibility, whitespace, links, public-file/private-artifact checks and remote commit verification accompany release; no learning guides or generation/OCR/trust features were added.

## Part 5 local-answer evidence

Application upgrade to `0004_answers`, repeated upgrade and exact in-memory comparison preserved users, sessions, versions, pages, provisional chunks, audited reviews and retrieval generations/passages/state. No reset or reprovisioning. The baseline remains four versions/171 pages/410 provisional chunks, one eligible historical source/nine vectors and three excluded sources. Only additive owned-answer/worker tables were introduced.

Ollama 0.17.1 was already installed; its personal 11434 service and existing larger model were preserved and not used. Only official Qwen3 4B Instruct 2507 Q4_K_M was prepared in the separate project store. Actual digest/settings and pinned Qwen tokenizer are in [model record](llm_model.json). Loopback 127.0.0.1:11435 verified. No second E5 model, paid/cloud generation, second candidate download or CUDA Python stack.

### Real source samples and manual review

Read-only [answer runner](../backend/evaluate_answers.py) uses the twelve-case Part 4 development set, with an explicit 2025-document prefix on the eight grounded English/Hindi cases. Final constrained one-claim run returned eight schema/span-valid results: annual support page 2, objectives page 3 (Hindi also cited page 2), face authentication page 4 and chatbot page 5. These are **not eight independently verified factual answers**. The implementing agent inspected all eight generated claims against their exact quoted spans. Independent human review is pending.

Annual examples described Rs 6,000/year and three instalments in both languages. English face authentication retained 2023 and “without OTP or fingerprint”; Hindi retained that negation. EKstep/Bhashini names were preserved in the final bilingual chatbot samples. Exact page/excerpt offsets and basic values were checked, with no invented URL or trust percentage displayed.

Known manual-review issues: objectives outputs omit some small/marginal-farmer qualifiers; Hindi objectives has poor grammar and broadens “moneylenders” to “bankers or other moneylenders.” This demonstrates that ID/span/numeric validation does not establish semantic faithfulness or complete beneficiary scope. Earlier development runs had Hindi truncation at the 768-token cap, name transliteration errors and one planned-event/completed-event tense error. Prompt refinement reduced adjacent claims and final samples did not truncate, but those failure modes are not proven eliminated. This is development tuning on one source, not held-out accuracy, a hallucination percentage or a proposal-target result. Full semantic support/date-value association remains Part 6; broader Hindi/Hinglish quality remains Part 7.

Both ambiguous cases clarified without generation. Both out-of-corpus Neptune cases abstained. Additional English/Hindi present-day amount/eligibility cases and a no-match filter abstained without generation. Historical-source notices and context omission notices remained visible. Keyword intent checks and similarity cutoff are uncalibrated and cannot guarantee all unsupported questions are caught.

### Measured execution

Final sequential eight-sample run: cold first pipeline 9.339 s, including Ollama load 3.782 s. Subsequent seven pipeline totals 5.393–11.205 s, median 5.929 s; warm model load 107–141 ms. Output generation rate 37.50–40.33 tokens/s (actual eval_count/eval_duration), prompt counts 2662–3188 and output counts 130–360. All successful calls matched exact pinned-Qwen preflight prompt counts, with raw template/schema/system/evidence included. Whole lower-ranked passages were omitted when necessary; no condition text was clipped. Totals include retrieval/validation/IPC, exclude browser rendering and worker polling. Separate worker startup/tokenizer initialization and system load vary; these timings are not throughput guarantees.

Actual `/api/ps` reported 3,515,036,800 bytes for both model size and size_vram at context 4096, establishing full GPU residency on this RTX 4050 run. `nvidia-smi` sampled 3153 MiB total GPU use and 96% utilization after the recovery inference; it uses a different accounting basis from Ollama. During the preceding final-prompt development run, project server working set was 69,959,680 bytes and runner 762,441,728 bytes (combined about 794 MiB), with individual reported peaks 72,232,960/794,910,720 bytes. These are process samples, not a continuously measured system RAM peak or hard quotas. The personal instance was excluded. GPU inference worked, so CPU generation fallback was not exercised; E5 remains CPU/two threads.

### Failures, privacy and cleanup

Real isolated user/document injection selected no factual claims; synthetic instructions never entered the application corpus, SQL source tables or vectors. Unit tests also check escaped Qwen control tokens and omission of high-signal instruction paragraphs. This limited test does not establish general injection resistance.

Actual in-flight inference was cancelled after 0.5 seconds; the owned Windows process tree was replaced in 3.157 s, and the fresh instance reported zero loaded models before a successful new request. A separate actual 0.5-second deadline cancelled generation, replaced the tree and again showed zero loaded models; another successful request followed. Stopping the actual server produced `ollama_unavailable` and restart recovered. The full 120-second worker timeout was exercised with a shortened one-second deadline and a slow test double, not a 120-second manual wait. Single-pending busy behavior, cross-user 404/empty history, source archive during generation, changed history warnings, interrupted-worker recovery and 30-day retention used isolated PostgreSQL fixtures. Adapter doubles cover digest/runtime/count mismatch, truncation/thinking/oversized output and timeout/offline errors. Bounded JSON repair and invented ID/quote/number/date/currency/negation rejection are tested independently of real-model quality.

All prior authentication, ingestion, actual E5/vector and PostgreSQL regressions passed. Full regression found and fixed startup heartbeat autoflush before the final 84-test pass. Production frontend build initially hit Windows sandbox parent-path read restrictions; rerunning with authorized read access succeeded. One existing upstream deprecation warning remains. Private model/corpus/history/report files stay ignored; raw prompts and reasoning are not stored. Relative documentation links, command entrypoints and public-artifact checks are part of release review.

Browser Ask used the existing private admin session: English and Hindi annual-support answers showed the official source, physical page 2 and exact [0, 1056) quote. One alternate Hindi wording returned grounding_validation_failed with no answer; a transient fetch error recovered. Current Hindi entitlement abstained and ambiguous English intent clarified. Owned history and its Hindi answer detail survived actual API/RAG process restart and page reload; no credentials were entered or published.
Browser cancellation reached cancelled with no answer. Existing Hindi Search still returned exact historical passages and admin access/document ingestion remained available.

## Part 6 claim/citation evidence (2026-10-06)

Additive `0005_citations` and repeated upgrade compared every existing table row in memory before/after, including private answer histories and worker/auth state. All were unchanged; zero historical claims/citations were backfilled. Four versions/171 pages/410 provisional chunks, nine indexed passages, one eligible historical PIB source and three excluded sources remain unchanged. No account provisioning, extra model, OCR or trust score.

### Support development measurements

[35-case support set](support_devset.json) and [read-only runner](../backend/evaluate_support.py) use the original eligible factsheet checksum/physical pages. Claims/labels were source-reviewed by the implementing agent and tuned during development; independent human validation and held-out evaluation are pending. Nine positives cover English/Hindi annual benefit, negation, named organisations, SMF objectives and equivalent Indian cumulative-number formatting. Twenty-six negatives cover amount/currency/frequency, instalment count versus national total, recipients/omitted conditions, negation, current/historical scope, jurisdiction/year, unrelated/edited quotes, insufficient quote, Hindi meaning, isolated conflict/supersession and the observed browser failure below. Synthetic mutations never entered application source tables/vectors.

Final `layered-qwen-v2` run with the same pinned Qwen/digest:

| Measure | Result / denominator |
| --- | --- |
| False accepts | 0/26 agent-labeled negative candidates |
| False rejects | 0/9 agent-labeled positive candidates |
| Exact SQL provenance | 34/35 attempts; the one intentionally fabricated quote failed before judging |
| Retained candidate coverage | 9/35 overall (25.7%); 9/9 positives; this challenge mix is not normal-user answer coverage |
| Judge calls | 12/35 cases; guards/provenance handled the remainder |
| Judge-case wall latency | median 1.512 s, range 1.359–4.612 s (first cold); includes source lookup/check and inference |

These results do not establish a hallucination target, general multilingual accuracy or independent truth verification. Guard/judge tuning used this same set. Conflicts are limited to selected same-scheme annual contexts and explicit source relationships, not exhaustive legal conflict detection. Judgment can still miss incorrect meaning.

A separate real-source two-candidate fixture retained the valid annual benefit and removed monthly ₹6,000: `partial`, 1/2 candidate retention, one judge call. Production generation still permits one claim. Four real generation-plus-support questions returned two retained English claims (annual benefit with land-holding restriction, SMF objective), one Hindi annual candidate removed for omitted land-holding scope, and one Hindi face-authentication abstention generated with zero claims. Thus 2/3 generated candidates retained and 2/4 queries produced claims; all 2/2 retained claims had exact original citations. No rejected policy prose was shown.

Warm pipeline totals were 6.198 s English annual, 5.788 s English objectives, 4.681 s Hindi annual rejection and 1.986 s Hindi zero-claim abstention. Added support-stage time was 1.741/2.006 s for retained English claims and 43.61 ms for the Hindi deterministic rejection; no support call for zero claims. These include real-source SQL gates/IPC and exclude browser rendering/polling. No matched counterfactual or throughput benchmark is claimed. Judge raw prompt counts matched the pinned tokenizer exactly; 256 output/64 safety tokens fit the existing 4096 context without clipping. GPU/runtime architecture and manifest are unchanged; no new memory-profile claim.

### Observed false accept and conservative correction

Before release, the browser's scoped Hindi annual answer changed the recipient to “अधिकारी के खाते” and DBT wording to “डिजिटल लाभ”. Pre-release `layered-qwen-v1` accepted it: one manually identified false accept in that observed case. The earlier 34-case set had reported 0/25 false accepts and missed this failure. It is not hidden: the complete candidate is now a negative development case, recipient/DBT guards were added and the method advanced to `layered-qwen-v2`. The final added case is rejected for scope mismatch. This is further development tuning, not fresh held-out success.

Existing private v1 answer/assessment remains unchanged and shows its recorded method; citation views identify when the current method differs and state that no reassessment occurred. Part 5 answers remain `not_evaluated`. This known failure demonstrates why same-model agreement is not independent corroboration. Hindi grammar and interpretation remain limited; correct bilingual hand-labeled support inputs passing does not imply reliable Hindi generation.

### Regression and browser checks

Final full suite: **107 passed, one existing upstream TestClient deprecation**, 56.35 s. Required pip check, TypeScript and production Vite build passed. Build initially encountered the Windows sandbox's parent-directory read restriction; authorized read access resolved it. Dedicated real PostgreSQL/actual E5 tests cover prior auth/ingestion/retrieval/answer behavior, exact-span persistence, stable IDs/index-rebuild inspection, partial filtering, legacy no-backfill, cross-user 404, normal-user text/admin-only originals, source archive and appended review change during support, missing/changed provenance redaction, timeout/unavailable/invalid verifier errors and no published answer. Verifier failure tests use controlled doubles; they do not measure a real 30-second model timeout. Real model checks exercised bounded generation/judging; Part 5's actual contained cancellation/offline recovery evidence remains applicable and is recorded above.

Browser checks used the existing private session, without entering/publishing credentials: legacy answer showed `not_evaluated` and opened actual page 2; new English annual claim showed numbered marker, valid SQL provenance, bounded heuristic support, version/date/applicability and original [0,1056) page text. The pre-release Hindi false accept is documented above; final revised browser behavior is recorded below. Current-policy abstention/clarification and reload/history flows were checked. Source revocation was tested only in isolated SQL fixtures, not by changing the live source review. React renders source/model text as text, not trusted HTML. Public-file/secret, relative-link/command and remote-hash checks accompany release; raw reports, corpus, models/vectors and private snapshots stay ignored.

Final browser repeat of the same scoped Hindi question returned `insufficient_evidence`, candidate omitted for `scope_mismatch`, with no rejected factual text shown. Its total worker time was 10.610 s including cold generation. Opening the preserved v1 history showed the earlier-method/no-reassessment notice. New English browser annual claim had exact page-2 inspection (earlier measured worker total 10.117 s); legacy Part 5 inspection remained not_evaluated.

Final v2 English browser request took 6.020 s total, retained the land-holding/₹6,000/year/three-instalment claim, and opened exact page 2 with `layered-qwen-v2`. Current Hindi entitlement abstained and ambiguous English intent clarified.
Final v2 answer and complete citation/source inspection text matched exactly after authenticated browser reload and history reselection.


## Part 7 — multilingual input and versioned OCR (2026-10-06)

### Environment and preserved state

Same Windows/PostgreSQL 18.6, pinned multilingual E5-small CPU/two-thread encoder, Chroma, Ollama 0.17.1 and pinned Qwen3 4B Instruct 2507 Q4_K_M as Parts 4–6. No additional language model, paid translator, fine-tuning or guard relaxation. Tesseract 5.4.0.20240606/Leptonica 1.84.1 and official pinned fast English/Hindi packs were actually executed; hashes/licenses are in [SOURCES](SOURCES.md). Private preparation records the per-user executable and pack paths. Runtime startup performs no downloads.

Additive migration `0006_language_ocr` and repeated upgrade were run against the existing application database. An in-memory comparison of every original column/row across 18 tables remained identical. Existing users/sessions, originals, 171 original pages, 410 provisional chunks, rights reviews and historical answer snapshots were not reset/reparsed/backfilled. The four-version corpus remains one eligible historical PIB narrative-text source/nine indexed passages and three excluded sources.

### Real OCR measurements

Four self-authored image-only scan fixtures were rendered with installed Windows Nirmala.ttc, then processed by actual PyMuPDF/Tesseract `eng+hin`, 300 DPI, grayscale/PDF rotation, OEM 1, PSM 3, one thread. No scan/font/PDF binaries entered Git or the application corpus. CER and WER compare reference and actual text after whitespace normalization; raw engine TXT and word-box TSV remain preserved privately. CER is character edit distance/reference length; WER applies the same calculation to words.

| Fixture | CER | WER | Critical manual observation |
| --- | ---: | ---: | --- |
| English | 0 | 0 | Reference amounts, date, category, instalments and negation retained |
| Hindi | 0 | 0 | Reference amounts, date, category, instalments and negation retained |
| Mixed | 0.057554 | 0.041667 | `3 किस्तें` misread as `3 fed`; instalment meaning lost |
| Noisy Hindi | 0.020942 | 0.028571 | `वर्ष` misread as `a¥`; yearly frequency wording damaged |

All four passed the engine-signal legibility threshold, demonstrating why that threshold cannot establish transcription accuracy. Every OCR page still requires explicit critical-value/original comparison and an append-only admin decision. Labels/manual observations are implementing-agent review, not independent human evaluation or government-corpus accuracy.

Existing local files: six flagged pages attempted in two additive revisions. Five PMAY pages (2, 4, 6, 8, 111) yielded empty low-quality OCR; one PMJDY page (32) exceeded the 12-million-pixel limit. **Zero accepted/reviewed OCR pages; six excluded.** Both revisions remain partial. Their other **146 digital pages were copied exactly**. No ready extraction pointer or live index was switched. Restricted originals stayed restricted. OCR extraction is not reuse permission or current-policy verification.

Real isolated SQL/model/OCR tests cover physical-page preservation, unchanged digital text, mandatory review/rights gates, additive retry attempts/idempotency, stale lease fencing/resume, exact old citations across newer revisions/reindexing, failed-new-revision preservation, archive/rejection access, unauthorized/CSRF denial and token-aware E5 indexing. Actual short page deadlines, pixel caps and blank scans verify failure/temporary cleanup. A separately labeled controlled sleeper-descendant test verifies Windows Job tree termination; it is containment evidence, not a substitute for actual Tesseract smoke tests. Explicit live orphan reconciliation removed zero files. No hard RAM quota, malware sandbox, arbitrary deskew, table reconstruction or manual correction editor is claimed.

### Paired language development comparison

[language_devset.json](language_devset.json) has 24 cases: 15 grounded questions and nine ambiguous/outside/current-policy controls, including English/Hindi pairs, Roman variations, mixed/Devanagari digits, negation and beneficiary qualifiers. Gold spans were checked against the existing historical PIB factsheet by the implementing agent. The read-only runner used real E5/Chroma/SQL and pinned local Qwen with the unchanged Part 6 support stage. Baseline functions/prompt/token budget came from recorded Part 6 commit `31f64fdbfdbb7696f3fcc656634dc8588f0ad59d`; changed used the final implementation. Final two chatbot Hindi cases were rerun through actual index IPC/Qwen after manual proper-name/grammar correction; baseline rows remained fixed. Raw reports stay ignored in runtime.

| Metric | Baseline | Changed |
| --- | ---: | ---: |
| Grounded questions with gold-span hit in top five | 15/15 | 15/15 |
| Grounded questions retaining checked claims (`answered` or `partial`) | 7/15 | 14/15 |
| Controls returning clarification/abstention without claims | 9/9 | 9/9 |

There was **no demonstrated retrieval coverage gain**. Original rankings remain primary; normalized queries are compared and serve only as an empty-original fallback. Transparent normalization preserves the exact user question, safely maps bounded phrases/aliases/digits, and does not select response language. Explicit English/Hindi choice overrides profile; Hinglish profile maps to Hindi. Short scheme-name detection remains uncertain. The Roman current-policy control changes from clarification to abstention; neither variant supplies entitlement advice.

Improvement is primarily narrow final Hindi handling: complete annual-benefit paragraphs survive budgeting and an exact positive digital pattern supplies recipient/annual amount/count; a second exact digital chatbot paragraph preserves EKstep foundation/Bhashini and completed-development grammar. These constructions still require an already selected exact quote and unchanged final support checks, skip OCR and are not general translation. A family-specific question returns partial scope rather than inventing a family category. One Hindi objectives query still conservatively abstains. Other generated Hindi may remain awkward; checks are same-model heuristics and cannot guarantee meaning/current applicability. Interim tuning exposed proper-name/grammar errors and same-model false rejects, including confusing document publication year with a past event; final wording separates those scopes. Retention is not accuracy, P@5, a hallucination rate or held-out evaluation. Labels were reused for tuning; independent review remains pending.

The existing real-source 35-case support regression was repeated: zero false accepts among 26 negatives, zero false rejects among nine positives; 34/35 exact provenance valid, with the deliberate fabricated quote invalid. Selected-context conflict and two-candidate retention checks still passed. These are development guard regressions, not independent truth verification. Trust remains null.

### Release checks

After wake/resume, full required suite: **118 passed in 107.36 seconds**, one existing upstream Starlette/AnyIO deprecation; dedicated disposable PostgreSQL only. `pip check`: no broken requirements. Frontend typecheck and production build: 36 modules, build 2.69 seconds. Prior runs had Windows temporary/cache permission failures; fresh ignored test/cache directories resolved these without changing application data. Commands and service owner requirements are in [SETUP](SETUP.md).

Browser checks use the existing private admin session without exposing credentials. Protected original page 32/pixel-limit exclusion and empty PMAY page 2/disabled acceptance were inspected. Switching documents now clears old revision state and keys the component by version; the correct 112-page revision loaded. Final Hinglish annual question with explicit Hindi output returned the exact land-holding/6,000-yearly/three-instalment construction with historical/current-applicability warnings and heuristic support. Real worker total was 12.653 seconds in that browser run, not a throughput benchmark. Citation inspection opened original physical page 2, exact quote [0,1056), legacy digital revision and bounded preserved page text. Reload/history reopened the stored answer unchanged. Source revocation/reindex/OCR citation access changes were exercised in isolated tests, without modifying live rights. A fresh Roman current-entitlement question returned Hindi insufficient_evidence with no policy claim. The final Hindi chatbot query returned the source-preserving EKstep foundation/Bhashini sentence in completed-event wording. Initial stale browser error-tab recovery required a fresh same-browser tab; a sandbox-started frontend was replaced by the verified host-loopback owner, with no duplicate services. Screenshot proof remains ignored locally. Public-file/relative-link/command and final diff checks passed before commit/push; release hash is verified against remote main separately.

## Part 8 evidence-quality assessment (2026-10-06)

Baseline: clean Part 7 `ba453a3ea26bc61bb4bc10e3419ddbc7eb6f32ab`. Inspected proposal physical page 22; its six weights and badge thresholds are unvalidated. [Contract](TRUST_SCORING.md) implements only defensible numerical citation coverage, with descriptive support/date/source audit evidence. All other numerical components, full aggregate and partial index remain null. This release does not claim calibrated correctness, independent semantic verification, current entitlement or held-out accuracy.

### Database and regressions

Applied `0007_evidence_quality` to the existing application database, repeated upgrade, and compared every pre-existing column/row across 22 tables: unchanged. Existing answer snapshots were not rescored; 15 old records remained unassessed. Original corpus stayed four versions, 171 original pages, 410 provisional chunks and zero live OCR reviews. No new sources, rights changes, OCR acceptances, model downloads, configuration provisioning or data resets.

Final full suite: **127 passed in 68.67 seconds**, one existing upstream Starlette/AnyIO deprecation. Real safeguarded disposable PostgreSQL, existing offline E5/Chroma and actual Tesseract were used. Coverage fractions/bounds, absent dimensions/denominator, repair-attempt versus displayed-claim counts, duplicate versions/copies/chunks, known conflicts, legacy read-only behavior, snapshot copy/redaction, owner/unauthenticated denial, durable abstention/failure records and excluded OCR are checked. Existing corpus/review/auth/citation/recovery/resource regressions remain included. Controlled generators/judges isolate failure paths in tests; these are not accuracy measurements.

Nine contract tests were rerun after the final optional answer-status field/UI wording adjustment: passed in 0.04 seconds. `pip check`: no broken requirements. Frontend production build includes typecheck: 37 modules, final measured build 1.54 seconds. Documentation relative links/backend command paths, excluded-file/actual-private-secret scan and final diff whitespace review passed. Runtime proofs and synthetic scans remain ignored; no account identifiers/credentials are documented.

### Real Ask and History journeys

Used the existing private session, actual eligible historical PIB source, E5/index IPC and pinned Qwen. API, frontend, ingestion/index/answer workers were started only because missing. One owner/listener per project service was verified; personal Ollama on 11434 was preserved. English/Hindi panels show all six components and expandable method/count/source details. Actual 375-pixel layout uses one column; explicit 1280×900 breakpoint test uses two columns. Temporary viewport was reset.

| Browser question | Result | Candidate / retained / rejected audit records | Coverage | Available weight | Worker total |
| --- | --- | --- | --- | --- | ---: |
| According to the 2025 PM-KISAN factsheet, what annual assistance and instalments are described for land-holding farmers? | partial | 1 / 1 / 0 | 1/1 = 100% | 25% | 11,132.03 ms |
| 2025 PM Kisan factsheet ke anusaar saalana kitna paisa aur kitni kiste? (explicit Hindi response) | answered | 1 / 1 / 0 | 1/1 = 100% | 25% | 10,030.78 ms |
| aaj PM Kisan me paatra hun aur kitna paisa milega? (Hindi response) | insufficient_evidence | 0 / 0 / 0 | unavailable | 0% | 111.74 ms |
| Am I eligible for assistance? (English response) | needs_clarification | 0 / 0 / 0 | unavailable | 0% | 71.45 ms |

The first English result was partial despite full retained citation coverage; scope/completeness warnings stayed visible. Hindi retained the historical land-holding-farmers/6,000-yearly/three-equal-instalments wording. Source audit records one document/version, publication date 2025-08-01, unknown effective date, historical review, exact physical-page/span and digital extraction references. No independent-source count or policy-currency number is inferred. Faithfulness records `layered-qwen-v2`/`support-judge-v1`, not numerical accuracy. Calibration and feedback lack the required independent process/data. No overall/partial score or trust badge appears.

Restarted only the verified API/answer worker, reloaded and reopened the English assessment from history. A further API restart compared hashes of every saved result/source/assessment across all four new runs: unchanged, with original corpus counts and 15 unassessed historical records unchanged. The Hindi history record was also reopened. A genuine pre-Part-8 chatbot answer still displayed not evaluated with all values unavailable; no read-time backfill. Revoked-source and excluded-OCR assessment checks were isolated tests, not modifications to live rights/OCR records. Local screenshots remain ignored.

These four browser cases are smoke checks on one historical source, not an accuracy/currency benchmark or throughput measurement. Same-model semantic errors, incomplete answers, limited selected-context conflict detection, corpus breadth/rights and independent calibration/review remain unresolved. Future Part 9/10/11 work is not implemented here.
