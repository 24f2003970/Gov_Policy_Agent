# API conventions

Interactive schemas: `http://127.0.0.1:8000/docs`; machine schema: `/openapi.json`. [Authentication](../backend/app/auth.py), [documents](../backend/app/documents.py) and [retrieval](../backend/app/search_api.py) define the current contract.

Protected requests use `Authorization: Bearer <access-token>`. Mutations require the approved Origin and `X-CSRF-Protection: 1`. Browser requests include credentials for refresh cookies. Document routes require a live admin role; unauthenticated and non-admin requests return 401 and 403 respectively.

| Method / route | Purpose |
| --- | --- |
| GET /health/live, /health/ready | Process liveness; configured DB/schema/auth readiness |
| POST /auth/register, /auth/login | Normal-account registration; access token/user and refresh cookie |
| POST /auth/refresh, /auth/logout | Rotate session; revoke session and clear cookie |
| GET/PATCH /auth/me | Current user; preferred-language update |
| GET /auth/admin/access | Server-enforced admin access check |
| POST /admin/documents/upload | Validate/preserve original, return version and persisted job |
| GET /admin/documents, /admin/documents/{id} | Paginated documents and versions |
| PATCH /admin/documents/{id}/archive | Reversible archive state |
| GET /admin/documents/versions/{id}/status | Persisted job, metadata and future eligibility gate |
| GET /admin/documents/versions/{id}/pages | Paginated page/section summaries |
| GET /admin/documents/versions/{id}/pages/{ordinal} | Exact text window and paragraph spans |
| GET /admin/documents/versions/{id}/chunks | Provisional chunk text/offsets/profile |
| GET /admin/documents/versions/{id}/original | Integrity-checked original download |
| GET /admin/documents/versions/{id}/preview/{ordinal} | Protected rendered PDF page PNG |
| POST /admin/documents/versions/{id}/retry | Failed job below three attempts only |
| PATCH /admin/documents/versions/{id}/provenance | One-time verified/rejected decision and note |
| GET/POST /admin/documents/versions/{id}/relationships | Inspect/record explicit verified version relationships |
| GET/POST /admin/documents/versions/{id}/reviews | Admin audited history/correction: reason, evidence URL, reuse scope and applicability |
| GET /search/status | Authenticated SQL generation/progress/model and source exclusion reasons |
| POST /search | Authenticated, throttled candidate-passage retrieval |
| GET /search/versions/{id}/pages/{ordinal} | Normal-user exact text window, gated by active reviewed eligible generation |
| POST /admin/index/rebuild | Queue/reuse pending generation with a reviewed source snapshot |
| POST /admin/index/{id}/retry | Failed indexing job below three attempts only |

Upload uses raw bytes, `filename` query and URI-encoded metadata JSON in `X-Document-Metadata`, not multipart. Fields: title, issuer, optional scheme, document_type, source_url, language, nullable publication/effective dates, reuse_status and optional document_id for a new edition. Exact types/lengths are in OpenAPI. Same bytes/same snapshot return an existing version/job; conflicts return 409.

Text windows are at most 20,000 characters, with explicit offset/total and half-open spans. Document/page/chunk lists are bounded; details expose the latest 20 versions per page. Ingestion terminal states are completed, partial, needs_ocr or failed. Retrieval requires a latest audited verified rights review, completed extraction, active document and no explicit supersession. Append-only reviews correct effective eligibility without rewriting immutable version metadata; every new review requires a rebuild before that version returns again.

`POST /search` accepts `question` (2–2000 characters; <=512 actual prefixed tokens), `count` (1–10, default 5), optional exact `scheme`, `issuer`, `document_type`, ISO `published_after`/`published_before`, and `unknown_dates` (`exclude` default or `include`). Dates are publication bounds, not proof of current legal effect. Unknown-date choice applies when bounds are supplied. Input dates must be ordered. Mutating routes retain Origin/CSRF checks; search defaults to 50 requests per IP per 15 minutes and one runtime operation at a time.

Response `status` is `results`, `empty` or `unavailable`; results contain original question, generation/model spec, timings, labeled cosine distance/similarity and ranked exact text, document/version/chunk IDs, issuer/title/source URL, physical page, half-open character span, review scope and historical/unknown applicability. A 0.78 similarity cutoff is heuristic; no generated answer or trust score is returned. `empty` means no eligible candidate passed filters/cutoff, not proof that a policy does not exist. Busy/offline/mismatched service yields sanitized 503; oversized tokens yield 422. SQL status does not assert the separate service is running. Admin-only originals/previews are unchanged.

Errors use `{error: {code, message, request_id}}` and `X-Request-ID`; submitted IDs and private exception details are not reflected. Validation/size/conflict/service errors use 422/413/409/503. CORS preflight denial is the middleware's separate 400 response.

## Owned local answers

Defined by [Ask routes](../backend/app/ask_api.py); all require live authentication, with Origin/CSRF on POSTs.

| Method / route | Purpose |
| --- | --- |
| GET /ask/status | Worker heartbeat availability, pending limit 1, null trust |
| POST /ask | Queue one owned request; 202, or sanitized 503 offline/busy |
| GET /ask/history?page=1 | Owner-only summaries, 20 per page |
| GET /ask/history/{run_id} | Owner-only immutable result/source/model/timing snapshot and current source warnings |
| POST /ask/history/{run_id}/cancel | Cancel queued job or signal processing cancellation |

Input: Search question/filters/date rules, `language: en|hi` (default en), fixed `count: 5`. Throttling defaults to 50 Ask requests/IP/15 minutes. Generation is asynchronous: poll the returned record ID. States are `queued`, `processing`, `done`, `error`, `cancelled`; terminal result statuses are `answered`, `partial`, `needs_clarification`, `insufficient_evidence`. A failed job has a sanitized `error_code`, not a fabricated answer. Other-owner/missing IDs return 404; no global private-history listing exists.

Successful details include server-built answer/claims, exact quoted excerpt offsets, original passage/version/page/review metadata, pinned model/settings, prompt/schema/index revision and nanosecond Ollama counts/timings plus millisecond worker time. No raw prompts, reasoning or confidence percentages are returned. Trust is null. Historical snapshots carry limitations; later archive/review changes trigger current-source warnings. Terminal records expire at 30 days on worker startup/hourly cleanup.

Relevant job errors: `retrieval_unavailable`, `ollama_unavailable`, `llm_digest_mismatch`, `ollama_version_mismatch`, `llm_token_count_mismatch`, `context_budget_exceeded`, `generation_truncated`, `generation_timeout`, `grounding_validation_failed`, `source_status_changed`, `source_span_changed`, `worker_interrupted`, `queue_deadline_exceeded`. Cancellation publishes no policy answer. Full semantic support verification is deferred.
