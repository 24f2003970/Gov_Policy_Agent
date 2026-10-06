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
| GET /ask/history/{run_id} | Owner-only result/citations/checks/model/timings, with current-access redaction and source warnings |
| GET /ask/history/{run_id}/citations/{citation_id}/text | Exact authorized original-page text window for a retained citation, including historical index generations |
| POST /ask/history/{run_id}/cancel | Cancel queued job or signal processing cancellation |

Input: Search question/filters/date rules, `language: en|hi` (optional; profile default, Hinglish profile maps to Hindi), fixed `count: 5`. Throttling defaults to 50 Ask requests/IP/15 minutes. Generation is asynchronous: poll the returned record ID. States are `queued`, `processing`, `done`, `error`, `cancelled`; terminal result statuses are `answered`, `partial`, `needs_clarification`, `insufficient_evidence`. A failed job has a sanitized `error_code`, not a fabricated answer. Other-owner/missing IDs return 404; no global private-history listing exists.

Successful details include server-built answer/claims, exact quoted excerpt offsets, original passage/version/page/review metadata, pinned model/settings, prompt/schema/index revision and nanosecond Ollama counts/timings plus millisecond worker time. No raw prompts, reasoning or confidence percentages are returned. Trust is null. Historical snapshots carry limitations; later archive/review changes trigger current-source warnings. Terminal records expire at 30 days on worker startup/hourly cleanup.

Relevant job errors: `retrieval_unavailable`, `ollama_unavailable`, `llm_digest_mismatch`, `ollama_version_mismatch`, `llm_token_count_mismatch`, `context_budget_exceeded`, `generation_truncated`, `generation_timeout`, `grounding_validation_failed`, `source_status_changed`, `source_span_changed`, `worker_interrupted`, `queue_deadline_exceeded`. Cancellation publishes no policy answer. Additional errors: `verification_unavailable`, `verification_timeout`, `verification_invalid_output`, `citation_provenance_invalid`, `citation_context_missing`. Verification errors publish no policy answer; over-budget complete evidence produces `insufficient_context` and is not accepted.

Details include ordered `claim_checks` (stable claim ID, position, retained flag and assessment) and numbered `citations` tied to retained claims. Each citation separates `provenance`, `support`, `current_access` and recorded applicability/date metadata; exact quote and claim text are null when withheld. Rejected candidate text is never exposed. `support.method` is `layered-qwen-v2`; `judge_revision` is present only when called. `independent_verification` is false and trust remains null. Legacy answers show `not_evaluated` without persistent backfill.

Citation text returns the bounded original text window plus citation/quote offsets, actual physical page or TXT span, original paragraph spans and total characters. Owner mismatch/missing citation is 404; revoked current access is 403; missing/mismatched original provenance is withheld (history reasons) or 503 during final span validation. Current access is checked on every read. If any recorded source/review/provenance changes, history withholds the whole answer and all source/citation excerpt text; stored snapshots remain unchanged. Index rebuild alone does not revoke old-generation citations.

`current_support_method` identifies the running method. An earlier recorded assessment retains its original method/outcome; the citation panel warns about the mismatch and does not claim that the current method reassessed it.


## Versioned OCR

[OCR routes](../backend/app/ocr_api.py) require live admin authorization on **every** route and Origin/CSRF on POSTs. Normal users receive 403; no original image privilege is added.

| Route | Purpose |
| --- | --- |
| POST /admin/ocr/versions/{version_id}/queue | Queue/reuse pending revision for flagged PDF pages; requires prepared packs and initial extraction |
| GET /admin/ocr/versions/{version_id} | Latest 20 revisions, page progress/method/flags/signals/review |
| GET /admin/ocr/{revision_id} | Exact job state/spec and latest page attempts |
| POST /admin/ocr/{revision_id}/retry | Failed/partial below three attempts; reuse successful pages |
| POST /admin/ocr/{revision_id}/cancel | Fence queued/processing child; historical artifacts remain |
| GET /admin/ocr/pages/{page_id}/text?offset=0 | Immutable raw/digital text window, word boxes and labeled engine signals |
| POST /admin/ocr/pages/{page_id}/reviews | Append decision/reason; requires checked_values_dates_categories_negation=true |

Review accepts `decision: accepted|rejected`, reason (20–2000 chars) and the explicit critical-value checkbox. Low-quality OCR cannot be accepted. Review is disabled for active/cancelled/failed/archived jobs and superseded attempts. No text-editing/correction API exists. Complete means every original physical page is represented, successful digital text is preserved and every OCR page passes quality plus latest manual acceptance. Rights, official review, archive and supersession are independent gates.

Index passages and citations return `extraction_revision_id`, `extraction_page_id`, `extraction_method`, `extraction_quality_flags`, `extraction_review_status` and `ocr_notice`. The original physical page ID remains separate from the artifact ID. Normal Search inspection resolves the active generation's recorded artifact; owned historical citation inspection resolves its recorded artifact independent of the newest revision/index. Current rejection of that artifact blocks access. Legacy null artifact IDs resolve original digital pages without backfill.

Search/Ask preserve `question` and expose `retrieval_question`/`query_normalization`: revision, transformations, uncertain detection, ranking selection and original/normalized passage ID comparisons. Detection never controls response language. Ask timings record narrow Hindi annual complete-excerpt context selection, optional `annual-hi-digital-fields-v1`/`chatbot-hi-digital-names-v1` source-field response construction and up to two total generations, including a constrained condition/scope retry. Rejected attempts remain private; displayed text still passes Part 6 support. API failure/abstention/retention rules are unchanged.

## Evidence-quality payload

Owned Ask/detail responses include `evidence_quality`: schema/method/status, saved-snapshot indicator, nullable aggregates, available weight coverage, six component objects, counts and source references. Each component has value/availability/weight/method/explanation/evidence. Fractions lie in [0,1]; unavailable values remain null. [Contract](TRUST_SCORING.md) defines the calculation and statuses. Existing authorization/CSRF/ownership apply; there is no additional write or reassessment endpoint. History list summaries omit scores and references. Detail opens perform current access checks; source-unavailable responses hide all saved values/counts/references while preserving private SQL.

## Saved answer bookmarks

All routes require an active authenticated user; guessed foreign answer IDs return 404 regardless of admin role. PUT/DELETE also require existing exact-origin/CSRF headers. No public/export endpoint exists.

| Route | Behavior |
| --- | --- |
| GET /ask/history?page=1 | Owned history summary, 20/page; returns items/page/has_next/total |
| GET /ask/saved?page=1 | Owned bookmarks, 20/page, stable bookmark-time/id ordering; summaries add saved_at and current available flag |
| PUT /ask/history/{run_id}/saved | Idempotent save; 200 returns current protected detail; 409 if status/content/current source access/30-day eligibility fails |
| DELETE /ask/history/{run_id}/saved | Idempotent removal even when sources are withheld; 200 returns current protected detail |
| GET /ask/history/{run_id} | Shared History/Saved protected detail; adds saved and can_save; existing source redaction and assessment contract apply |

Answered/partial terminal results need nonempty claims and accessible citations. Unassessed older factual results remain unassessed. Saving does not refresh the original answer creation/expiry date. Deleting an answer during normal worker retention cascades its bookmark. Concurrent writes serialize on the parent answer; the last database-serialized membership change wins, not necessarily the request that arrived last. Duplicate saves preserve saved_at. Pagination rejects page <1; an out-of-range positive page is empty. Saved summaries omit expired answers and never include quote text or scores. History uses existing retention cleanup timing. No endpoint reassesses a historical answer.
