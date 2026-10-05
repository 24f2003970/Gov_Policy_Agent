# Recorded verification

Executed 2026-10-05 on Windows 11/PowerShell 7.6.5, Python 3.12.14, Node 24.12.0/npm 11.6.2 and PostgreSQL 18.6. These are recorded implementation checks, not new test runs during documentation cleanup.

| Release | Backend | Other checks |
| --- | --- | --- |
| Foundation (Part 1) | 14 passed; clean lock install repeated | npm ci, TypeScript/build, browser connected/disconnected/recovered, mobile/desktop review |
| Authentication (Part 2) | 32 passed in 7.44s, including 16 real PostgreSQL cases | pip check, TypeScript/build, actual browser account/role/session flows |
| Ingestion (Part 3) | 56 passed in 22.84s, real PostgreSQL and parser/claim processes | pip check, TypeScript/build (33 modules), admin upload/inspection/preview/retry/archive |

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

No answer-quality, retrieval, OCR, table reconstruction, throughput, memory, multi-worker resource, public deployment or production-security evaluation. Malware scanning, OS parser sandbox and hard memory quota are unavailable. Health snapshot and transient recovery checks do not prove continuous monitoring or all timeout paths. Origin checks do not prove permission to reproduce sources.

Implementation releases were reviewed for ignored/private artifacts and pushed without force; commit identifiers are in [maintainer state](MAINTAINER.md). Documentation cleanup validation covers links, command references, whitespace and documentation-only diff scope; it does not rerun application tests or alter measured results.
