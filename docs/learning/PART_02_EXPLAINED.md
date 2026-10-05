# Part 2 samjho: accounts, database aur permissions

## 1. Previous part se kya add hua

Part 1 mein library reception tha. Part 2 ne membership register aur access rules add kiye. Ab users register/login kar sakte hain, language preference save kar sakte hain aur logout kar sakte hain. PostgreSQL data ko program restart ke baad bhi rakhta hai. Admin-only endpoint normal users ko deny karta hai.

Yeh existing Part 2 implementation ka explanation hai; accounts, provisioning ya admin ko recreate nahi kiya gaya. Current project Part 3 schema bhi use karta hai. Historical Part 2 release aur current behavior ke difference clearly indicated hain.

## 2. Basic concepts

| Term | Simple meaning | Everyday example |
| --- | --- | --- |
| Database | Structured records ki durable storage | Library ka membership register |
| Table/row/column | Record type / ek record / uska field | Members / ek member / email |
| SQL | Database se read/write karne ki language | Register mein specific member dhoondhne ka instruction |
| PostgreSQL | Actual database server | Register ko reliably manage karne wala system |
| SQLAlchemy | Python objects aur SQL records ke beech interface | Python member object ko database row se connect karna |
| Migration | Database structure ka versioned change | Register mein naya column controlled tarike se add karna |
| Alembic | Migrations apply/track karne ka tool | Register editions ka record |
| UUID | Large unique identifier | Har member ka unique reference number |
| Authentication | Tum kaun ho, verify karna | Membership card aur identity check |
| Authorization | Tum kya kar sakte ho, check karna | Member books le sakta; librarian catalog manage kar sakta |
| Hash | Input ka one-way derived value | Original recover kiye bina comparison karne ka fingerprint |
| Session | Ek active login ka durable record | Issued membership access pass ka status |
| Transaction | Related changes ko together commit/rollback karna | Pass cancel aur record update dono saath successful hona |

Passwords ke liye Argon2id slow, salted password hash use hota hai. Refresh tokens already random/high-entropy hain, isliye unke digest ke liye SHA256 use hota hai. Dono hashes ka purpose different hai. Hash encryption nahi: password decrypt karke recover nahi hota.

## 3. Login se logout tak actual flow

1. Register form email, username aur password backend ko bhejta hai.
2. Backend email lowercase/trim aur username Unicode-normalize/lowercase karta hai. Password 12–128 characters hona chahiye; truncation nahi hoti.
3. Submitted extra `role` reject hota hai. Public signup **user** role hi create karta hai.
4. Argon2id hash PostgreSQL `users` row mein save hota hai; plaintext password nahi.
5. Login par durable account/IP throttle attempt count check hota hai. Wrong password par generic 401 milta hai.
6. Successful login `auth_sessions` record create karta hai. Short access JWT frontend memory mein aata hai; random refresh token HttpOnly cookie mein.
7. Protected request JWT bhejti hai. Backend signature/claims aur current DB session/user status/role dono check karta hai.
8. Reload par memory token gayab hota hai; refresh cookie se server naya access token aur rotated refresh cookie issue karta hai.
9. Logout session revoke karta hai aur cookie clear karta hai. Old access JWT unexpired ho tab bhi revoked session deny hoti hai.

## 4. Tokens, cookies aur protection simple words mein

JWT digitally signed short access pass hai. Signature modified pass reject karti hai. Fixed HS256 algorithm, issuer, audience, expiry, subject aur session ID required hain. JWT ko encrypted private document mat samjho; client fields read kar sakta hai. Default access life 10 minutes hai.

Refresh token default seven-day absolute session ke liye random value hai. Database mein uska plaintext nahi, digest hai. HttpOnly cookie ko JavaScript directly read nahi kar sakta. SameSite=Strict aur `/auth` path cookie bhejne ki scope reduce karte hain. Local HTTP development mein Secure false; production configuration Secure/HTTPS require karti hai.

CSRF ka matlab browser ki existing cookie use karke unwanted mutation karwana. Project har auth mutation par approved exact Origin aur `X-CSRF-Protection: 1` require karta hai. Browser fetch `credentials: include` use karta hai. XSS phir bhi authenticated actions kar sakta hai; HttpOnly sab browser risks solve nahi karta.

Refresh rotation old token replace karti hai. Row lock ek session par concurrent rotations serialize karta hai. Known old token reuse entire session revoke karta hai. Arbitrary guessed token kisi session ko revoke nahi kar sakta. Frontend single in-flight refresh promise aur Web Locks same-origin tabs ki cookie operations serialize karte hain. Protected request maximum one refresh plus one retry karti hai.

## 5. Files aur connections

| File | Responsibility |
| --- | --- |
| [models.py](../../backend/app/models.py) | Users, sessions, throttle SQLAlchemy tables |
| [schemas.py](../../backend/app/schemas.py) | Registration/login/profile validation and safe response schemas |
| [auth.py](../../backend/app/auth.py) | Hashing, JWTs, CSRF, live authorization, throttle, rotation, logout |
| [database.py](../../backend/app/database.py) | Safe URL.create connection, small pool, sessions and schema readiness |
| [config.py](../../backend/app/config.py) | SecretStr settings, loopback DB host, CORS and production cookie rules |
| [manage.py](../../backend/manage.py) | Hidden-input first-time DB provisioning and first-admin bootstrap |
| [0001_auth.py](../../backend/migrations/versions/0001_auth.py) | Explicit initial auth schema migration |
| [migrations/env.py](../../backend/migrations/env.py) | Alembic database connection/metadata setup |
| [auth.ts](../../frontend/src/auth.ts) | Memory tokens, API calls, refresh retry, Web Locks/BroadcastChannel |
| [AuthApp.tsx](../../frontend/src/AuthApp.tsx) | Forms, account page, navigation and admin permission check |
| [test_auth_postgres.py](../../tests/test_auth_postgres.py) | Genuine PostgreSQL auth behavior tests |
| [test_security_config.py](../../tests/test_security_config.py) | Secure production config and password boundaries |

## 6. Important tables/functions/endpoints

| Table | Kya save hota hai | Kya save nahi hota |
| --- | --- | --- |
| `users` | UUID, normalized unique identity, hash, user/admin role, language, active flag, timezone timestamps | Plaintext password |
| `auth_sessions` | User FK, refresh digest/consumed digests, expiry, revoked/rotation timestamps | Plaintext refresh token |
| `auth_throttles` | HMAC account/IP key, attempts, fixed-window start | Raw email/IP throttle identifier |

FK means foreign key: related user ka ID; database broken references prevent karti hai. Unique means duplicate normalized identity reject hogi. Timezone-aware timestamps batate hain event kis absolute time par hua.

| Endpoint/function | Input | Output/purpose |
| --- | --- | --- |
| `POST /auth/register` | JSON identity/password/language; Origin+CSRF | 201 safe user response, normal role |
| `POST /auth/login` | JSON email/password; Origin+CSRF | Access token/user + refresh cookie, ya 401/429 |
| `POST /auth/refresh` | Cookie; Origin+CSRF | Rotated cookie/new access token, ya 401 |
| `POST /auth/logout` | Cookie and optional access token; Origin+CSRF | 204, revoke session, clear cookie |
| `GET /auth/me` | Bearer JWT | Current safe user profile, ya 401 |
| `PATCH /auth/me` | Language + bearer + Origin/CSRF | Updated profile; role change rejected |
| `GET /auth/admin/access` | Bearer JWT | Actual admin authorization; missing session 401, normal user 403 |
| `current_user` / `admin_user` | Request + DB session | Check current session/active flag/role |
| `throttle` | Request account/IP/action | Durable bounded count, expiry/reset, optional 429 |
| `make_engine` | Private settings | Psycopg/SQLAlchemy pool with bounded timeouts |

## 7. Choices aur limitations

Native PostgreSQL 18.6 use hua; Docker engine prerequisite nahi. App `gov_app`/`gov_policy` aur tests `gov_test`/`gov_policy_test` use karte hain. Neither role has superuser, role-creation, DB-creation or replication privilege. App role own database schema migrations manage kar sakta hai; yeh PostgreSQL administrator nahi hai.

Sync database/password work FastAPI worker threads mein hota hai, event loop par nahi. Small pool laptop load bound karta hai. SQLAlchemy URL.create password punctuation safely handle karta hai; manual connection URL string escape karna nahi padta. Actual secrets ignored `.env` mein hain.

Default throttle five account login attempts per 15 minutes; all attempts count, successful bhi. IP limit 10 times account limit hai. Limits expire, permanent account lockout nahi. Uvicorn `--no-proxy-headers` client-supplied forwarded IP spoofing avoid karta hai. Throttle records cleaned/bounded hain.

Refresh history maximum 256 consumed tokens hai; uske baad re-login. Web Locks absent ho toh racing tabs session revoke kar sakte hain. Public deployment/TLS/full security evaluation later phases mein hain. Third-party OAuth/social login implement nahi hua.

## 8. Exact commands aur expected results

Current machine par DB setup/admin already done. **Configure ya bootstrap rerun karke existing accounts replace karne ki zaroorat nahi.** Fresh installation ke hidden-input steps [SETUP_PART2.md](../SETUP_PART2.md) mein hain.

Repository root PowerShell:

```powershell
Set-Location 'C:\Users\thiss\OneDrive\Documents\ChatGPT\Gov_Policy_Agent'
Get-Service postgresql-x64-18
& 'C:\Program Files\PostgreSQL\18\bin\pg_isready.exe' -h 127.0.0.1 -p 5432
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini current
```

Expected Running service, accepting connections, and **current head `0002_documents`** after Part 3. Historical Part 2 head was `0001_auth`. Upgrade repeats safely; downgrade can delete phase data and should not be casually run on application DB.

Only when bootstrapping a fresh installation's first admin:

```powershell
.\.venv\Scripts\python.exe backend\manage.py bootstrap-admin
```

Prompt asks identity and hidden password twice. It refuses when an admin already exists. No password arguments/default credentials are used.

Terminal 1, root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Terminal 2, root then frontend:

```powershell
Set-Location frontend
npm.cmd run dev
```

Root verification terminal:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pip check
```

## 9. Use aur actual verification

Browser `http://127.0.0.1:5173/#register` par normal account create karo; `/#login` par login. `/#account` language save karta hai. Reload par session restore hona chahiye. Logout ke baad protected account page sign-in required dikhayega. Normal user ko admin navigation nahi; direct `/#admin` par backend denial milta hai. Admin account par actual admin result aata hai; current Part 3 document UI uske neeche hai.

Recorded Part 2 release: **32 tests passed** (16 foundation/config/security and 16 real PostgreSQL cases), pip check and frontend typecheck/build passed. Real browser register, wrong password, login, preference, reload, logout, normal-user denial and privately entered admin login passed. Actual backend PID 22712 to 13620 restart ke baad session restored. Commit `fedc1c43a38324795f1d61a7348c2274407006ff` remote main par verified tha.

Tests expired/tampered/issuer/audience/algorithm/missing-claim JWTs, role injection, hashes, duplicate identity, disabled users, refresh replay/concurrency, CSRF, throttling, DB unavailable and missing-schema readiness check karte hain. They use the exact dedicated disposable test DB, never application reset. Current Part 3 suite updated full schema ke against same auth regressions run karti hai. Upstream TestClient deprecation warning remains; no production penetration-test claim.

## 10. Common problems

| Problem | Fix |
| --- | --- |
| Invalid email/password | Actual registered email/password use karo; account auto-create nahi hota |
| 429 too many attempts | Fixed window expire hone do; repeated guessing mat karo |
| 401 after expiry/logout | Sign in again; revoked session intentionally rejected hai |
| 403 admin role required | Normal user expected denial; UI link se role change nahi hota |
| CSRF/Origin 403 | Browser 127.0.0.1:5173 use karo; non-browser requests exact headers require karti hain |
| Ready 503 | Service, ignored private config and current explicit migrations check karo |
| Bootstrap says failed | Existing first admin, duplicate identity, input/service/config check privately; password chat mein mat bhejo |

## 11. Beginner viva

1. **Database kyun?** Accounts aur sessions restart ke baad persist hote hain.
2. **Password hash kyun?** Plaintext password store kiye bina verification ke liye.
3. **JWT kya hai?** Short-lived signed access pass.
4. **Refresh token alag kyun?** Reload/expiry par short access token safely renew karne ke liye.
5. **HttpOnly kya karta hai?** JavaScript ko refresh cookie read karne se rokta hai.
6. **Rotation kya hai?** Refresh token consume karke naya token issue karna.
7. **Logout ke baad unexpired JWT kyun fail?** Backend persisted revoked session bhi check karta hai.
8. **401 vs 403?** Valid authentication missing vs authenticated user ki permission missing.
9. **Admin role signup se kyun nahi?** Public user ko khud privilege grant karne se rokna hai.
10. **Alembic kyun?** Schema changes explicitly/versioned apply karne ke liye.

## 12. Bolkar explain karo

“Part 2 ne durable accounts aur permissions add kiye. PostgreSQL users aur sessions store karta hai. Passwords Argon2id se hashed hain, short JWT memory mein aur rotating refresh token HttpOnly cookie mein hai. Backend har protected request par current session aur role check karta hai. Isliye logout, disabled account aur normal-user admin denial actual server rules hain. Real PostgreSQL aur browser tests se behavior verify hua.”
