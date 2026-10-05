# API conventions

Interactive schemas: `http://127.0.0.1:8000/docs`; machine schema: `/openapi.json`. [Authentication routes](../backend/app/auth.py) and [document routes](../backend/app/documents.py) define the current contract.

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

Upload uses raw bytes, `filename` query and URI-encoded metadata JSON in `X-Document-Metadata`, not multipart. Fields: title, issuer, optional scheme, document_type, source_url, language, nullable publication/effective dates, reuse_status and optional document_id for a new edition. Exact types/lengths are in OpenAPI. Same bytes/same snapshot return an existing version/job; conflicts return 409.

Text windows are at most 20,000 characters, with explicit offset/total and half-open spans. Document/page/chunk lists are bounded; details expose the latest 20 versions per page. Job terminal states are completed, partial, needs_ocr or failed. Future retrieval eligibility requires completed extraction, verified provenance, permission_recorded and active document; no retrieval endpoint exists.

Errors use `{error: {code, message, request_id}}` and `X-Request-ID`; submitted IDs and private exception details are not reflected. Validation/size/conflict/service errors use 422/413/409/503. CORS preflight denial is the middleware's separate 400 response.
