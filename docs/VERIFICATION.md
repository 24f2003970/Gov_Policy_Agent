# Recorded verification

Executed 2026-10-05 on Windows 11/PowerShell 7.6.5, Python 3.12.14, Node 24.12.0/npm 11.6.2 and PostgreSQL 18.6. Earlier phase rows retain historical results; the Part 4 row records the current implementation run.

| Release | Backend | Other checks |
| --- | --- | --- |
| Foundation (Part 1) | 14 passed; clean lock install repeated | npm ci, TypeScript/build, browser connected/disconnected/recovered, mobile/desktop review |
| Authentication (Part 2) | 32 passed in 7.44s, including 16 real PostgreSQL cases | pip check, TypeScript/build, actual browser account/role/session flows |
| Ingestion (Part 3) | 56 passed in 22.84s, real PostgreSQL and parser/claim processes | pip check, TypeScript/build (33 modules), admin upload/inspection/preview/retry/archive |
| Retrieval (Part 4) | 65 passed in 64.06s, including nine real-model/vector/PostgreSQL retrieval cases | pip check, TypeScript/build (34 modules), offline real-source evaluation and browser Search |

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

No generated-answer quality, OCR, table reconstruction, throughput, GPU inference, multi-worker resource, public deployment or production-security evaluation. Malware scanning, OS parser sandbox and hard memory quota are unavailable. Health snapshot and transient recovery checks do not prove continuous monitoring or all timeout paths. Origin checks do not prove permission to reproduce sources.

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
