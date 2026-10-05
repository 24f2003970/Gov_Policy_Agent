# Beginner walkthrough (Hinglish)

Part 1 flow below is historical. Part 2 mein database readiness required hai aur [SETUP_PART2.md](SETUP_PART2.md) current commands deta hai.

## Part 2 ko simple words mein samjhein

Password database mein plaintext nahi jaata: Argon2id uska salted hash banata hai. Login verify hone par short-lived JWT memory mein milta hai aur random refresh token HttpOnly cookie mein. Backend refresh token ka sirf SHA256 hash save karta hai, kyunki token already unpredictable random data hai; human passwords ke liye Argon2 zaroori hai.

JWT valid hone par bhi DB session/user check hota hai: logout, disabled account ya changed role immediately respected hota hai. Refresh rotation ek database transaction mein row lock leti hai, taaki do requests same token ko successful consume na kar sakein. Used token repeat ho toh session revoke hota hai.

Alembic migration schema ka versioned change hai. Server startup tables silently create nahi karta; explicit upgrade command use hota hai. Disposable test DB normal application data se alag hai. Browser navigation hide karna permission enforcement nahi—admin endpoint khud role check karta hai.

Five Part 2 viva questions:

1. **Password hash aur encryption alag kyun?** Hash one-way password verification ke liye hai; plaintext recover karne ki zaroorat nahi.
2. **Access aur refresh token kyun?** Access short-lived API permission deta hai; refresh carefully controlled session renewal deta hai.
3. **Logout JWT ko kaise rokta hai?** Backend every protected request par DB session revocation check karta hai.
4. **Migration kya hai?** Version-controlled explicit database schema change; fresh setup repeatable hota hai.
5. **401 aur 403 ka difference?** 401 valid session missing/expired; 403 valid user ke paas required permission nahi.

## Request ka flow

1. `frontend/src/main.tsx` React screen ko browser ke root element mein mount karta hai.
2. `App.tsx` open hote hi effect chalata hai. Effect ka matlab: screen render hone ke baad external backend se baat karna.
3. `health.ts` actual `/health/ready` ko fetch karta hai. HTTP status aur expected JSON shape dono check hote hain; sirf koi bhi 200 response milna enough nahi hai.
4. Backend `config.py` .env ko typed settings mein convert karta hai. Invalid environment ya unsafe CORS origin ho toh startup fail hota hai.
5. `main.py` request ko unique ID deta hai aur readiness response bhejta hai. Abhi database/model required nahi, isliye unki absence readiness fail nahi karti.
6. Browser success par Connected aur real request ID dikhata hai. Error/timeout par Disconnected; button se fresh check hota hai. Cleanup stale request ko cancel karta hai, taaki old response new state overwrite na kare.

TypeScript ki discriminated union se loading, connected aur disconnected state ka data clear rehta hai. Connected state mein health data required hai; disconnected mein error message. API result unknown hota hai, runtime validation ke baad hi UI use karta hai.

## Important concepts

- **Frontend:** jo browser mein dikhta hai. **Backend:** jo API request process karta hai.
- **CORS:** browser ko permission dena ki kaunsa origin API response read kar sakta hai. Port bhi origin ka part hai. CORS authentication ka replacement nahi hai.
- **Environment configuration:** address/settings code edit kiye bina change karna. Secret .env Git mein nahi jaati; VITE_ values secret nahi hoti.
- **Request ID:** ek API request ka tracing label. Error report mein same ID se relevant log find kar sakte hain.
- **Liveness vs readiness:** liveness process alive hai; readiness current phase ka kaam serve karne ko ready hai. Future services abhi required nahi hain.
- **Lockfile:** exact dependency versions save karta hai, taaki next install reproducible ho. Tests bhi zaroori hain; lockfile correctness prove nahi karta.
- **Modular monolith:** ek backend process, andar focused modules. Beginner ke liye deployment/debugging manageable rehti hai.
- **RAG (later):** pehle verified passages retrieve, phir unke context se answer generate. Sirf similar passage milna claim ka proof nahi.

## Tests ko kaise samjhein

Tests actual API app ko TestClient se request bhejte hain. Yeh check karte hain ki health bina models ke chale, allowed origins ko permission mile, unsafe origins ko na mile, IDs unique hon aur errors private input/details leak na karein. Test-only routes sirf tests mein bante hain; production application mein nahi hain.

Browser verification alag hai: actual Vite aur Uvicorn processes chalakar Connected dekha, backend stop karke Disconnected, phir restart/retry se recovery check ki. Build pass hona akela browser connection ka proof nahi hai.

## Three viva questions

**Q1: Health live aur ready alag kyun?** Live batata hai process respond kar raha hai. Ready batata hai current required dependencies available hain. Abhi sirf validated configuration required hai.

**Q2: RAG abhi implement kyun nahi kiya?** Numbered development plan ke hisaab se pehle tested foundation banana hai. Database, verified evidence aur retrieval ke baad local generation add karenge.

**Q3: CORS aur request ID kya solve karte hain?** CORS approved browser origins ko response read permission deta hai. Request ID ek request ko trace karne mein help karta hai; dono authentication ya factual accuracy prove nahi karte.
