# Bazaura.pk Backend

REST API powering the Bazaura.pk React Native app and Next.js website.
Built with **FastAPI**, **SQLAlchemy 2 (async)**, **PostgreSQL** and **Alembic**.

- Clothing-first catalog (size/colour variants with per-variant stock), extensible to other categories
- Phone + OTP login with JWT access/refresh tokens
- Server-side cart pricing, vouchers, standard and express delivery (express window is configurable)
- Cash on Delivery orders with stock reservation and a tracking timeline
- Custom requests: "arrange this item for me" and "send a gift"
- SEO data for the website (slugs, meta tags, canonical URLs, sitemap feed)
- Staff/admin endpoints for the upcoming dashboard

## Quick start

```bash
make install                 # create .venv and install dependencies
cp .env.example .env         # then edit values
make db                      # start PostgreSQL in Docker (or point DATABASE_URL at any Postgres)
make migrate                 # create tables
make seed                    # optional sample catalog
make admin phone=03001234567 name="Your Name"
make dev                     # http://localhost:8000/docs
```

Without Docker, set `DATABASE_URL` in `.env` to a hosted Postgres (e.g. Neon) and skip `make db`.

In development `OTP_FIXED_CODE=123456` makes every login code `123456`; codes are also logged to the console.

## Project layout

```
app/
  main.py            App factory, middleware, health checks
  core/              Settings, database session, security helpers, error handling
  models/            SQLAlchemy models (database tables)
  schemas/           Pydantic request/response models (camelCase JSON)
  services/          Business logic (pricing, orders, auth, custom requests, catalog)
  api/
    deps.py          Auth, role and pagination dependencies
    v1/              Public endpoints, mounted at /api/v1
    v1/admin/        Staff/admin endpoints, mounted at /api/v1/admin
  utils/             Small pure helpers
migrations/          Alembic migrations
scripts/             seed.py, create_admin.py
tests/               API tests (pytest, in-memory SQLite)
docs/                API reference and the Roman Urdu guide
```

Routers stay thin; anything with business rules lives in `services/`. Services raise domain errors
from `app/core/exceptions.py`, which are rendered as a consistent error envelope.

## Conventions

- **Response envelope:** `{"success": true, "message": "...", "data": ...}`; errors add `"error": {"code", "details"}`.
- **JSON casing:** camelCase in and out (`fullName`); snake_case is also accepted in requests.
- **Money:** whole PKR integers. **Times:** ISO-8601 UTC.
- **Prices are never trusted from clients:** orders are re-priced on the server.
- **Tunable business rules** (fees, free-shipping threshold, express hours/cities) live in settings, not code.
  Frontends read them from `GET /api/v1/storefront/config`.

See [docs/API_REFERENCE.md](docs/API_REFERENCE.md) for every endpoint; live, interactive docs are at `/docs`.

## Common tasks

| Task | Command |
| --- | --- |
| Run tests | `make test` |
| Lint / format | `make lint` / `make format` |
| Add a DB change | edit a model → `make migration m="describe change"` → review the file → `make migrate` |
| Run the full stack in Docker | `docker compose up --build` |

## Deployment

The `Dockerfile` runs `alembic upgrade head` and then starts Uvicorn on `$PORT`, so it works as-is on
Railway, Render, Fly.io or any container host. Required production settings:

- `ENVIRONMENT=production` (disables `/docs`, enforces a strong `SECRET_KEY`, forbids `OTP_FIXED_CODE`)
- `SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS`, `SITE_URL`
- Storage (`STORAGE_*`) for image uploads and an SMS provider (`SMS_PROVIDER`) for OTP delivery

## Not in scope yet

Online payments (all orders are COD), push notifications, the admin dashboard UI.




Pehle samjho: app aur backend kaise judte hain
App ke andar koi data save nahi hota. App har screen ke liye backend se data maangti hai aur jo milta hai woh dikha deti hai:


App khulti hai → GET /storefront/home → banners, products → screen par dikhte hain
Isi wajah se backend se poori app control ho jati hai. Database mein jo badlega, app agli dafa wohi dikhayegi. App update karne ki zaroorat nahi padti.

Step 1: Backend ko internet par daalo (free)
Cheez	Free service	Note
Backend	Render (free web service)	GitHub repo connect karo. Hamari Dockerfile khud detect ho jayegi
Database	Neon (free Postgres)	Shuru ke liye kaafi storage
Images	Cloudflare R2	Free tier mein kaafi GB milte hain
Website	Vercel (Hobby)	Next.js ke liye
Free ki do haqeeqatein:

Render ka free server 15 minute koi request na aaye to so jata hai. Uske baad pehli request mein lagbhag 30–60 second lagte hain. Testing ke liye theek hai. Launch par sasta paid plan lena behtar hoga.
SMS free nahi hota. OTP bhejne ke paise lagte hain. Testing ke liye Firebase Phone Auth ka chhota free quota hai, ya OTP email se bhej sakte ho.
⚠️ OTP_FIXED_CODE=123456 sirf apne laptop par use karna. Agar ye public server par laga diya to koi bhi kisi bhi number se 123456 daal ke login kar lega. Isi liye ENVIRONMENT=production mein ye block hai.

Render ke Variables mein ye daalna hai:


ENVIRONMENT=production
SECRET_KEY=<lamba random>
DATABASE_URL=postgresql+asyncpg://...neon...?ssl=require
CORS_ORIGINS=["https://bazaura.pk"]
Deploy hone ke baad https://<naam>.onrender.com/health kholo. {"status":"ok"} aaye to backend live hai.

Step 2: React Native app mein backend lagao
Development mein, jab backend laptop par chal raha ho:


uvicorn app.main:app --host 0.0.0.0 --reload
Phone aur laptop ek hi WiFi par hon. App mein laptop ka IP do, jaise http://192.168.1.5:8000/api/v1.
Android emulator mein http://10.0.2.2:8000/api/v1 likhna hai.
App mein ek API client file banao. Ye ek hi jagah hogi, poori app isi ko use karegi:


// src/api/client.ts
import * as SecureStore from "expo-secure-store";

const BASE_URL = process.env.EXPO_PUBLIC_API_URL; // .env: EXPO_PUBLIC_API_URL=http://192.168.1.5:8000/api/v1

export async function api(path: string, options: RequestInit = {}) {
  const token = await SecureStore.getItemAsync("accessToken");
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  const body = await res.json();
  if (body.error?.code === "TOKEN_EXPIRED") {
    // yahan /auth/refresh call karo, naya token save karo, request dobara bhejo
  }
  if (!body.success) throw body.error;
  return body.data;
}
Teen zaroori baatein:

Tokens expo-secure-store mein rakho, AsyncStorage mein nahi. Secure store zyada mehfooz hai.
TanStack Query (React Query) library use karo. Ye loading, caching aur auto-refresh khud sambhal leti hai.
Native app ke liye CORS ka masla nahi hota. CORS sirf website (browser) par lagta hai.
Kaun si screen kaun si API call karegi:

Screen	API
App start	GET /storefront/config (fees, express ke 3 ghante)
Home	GET /storefront/home
Category / search	GET /products?category=men-hoodies&size=M
Product page	GET /products/{slug}
Login	POST /auth/otp/request, phir POST /auth/otp/verify
Cart	POST /cart/quote (har tabdeeli par)
Checkout	POST /orders
My orders	GET /orders, GET /orders/{id}
Gift / request	POST /custom-requests
Har API ki poori detail docs/API_REFERENCE.md mein hai.

Step 3: Backend se app kaise control hogi
Ye sab abhi se backend se control hota hai, app update kiye baghair
Badalna hai	Kaise
Naya product, price, photos	POST/PATCH /admin/products
Stock (size M khatam)	PATCH /admin/variants/{id}
Home ke banners	/admin/content
Voucher (WINTER500)	/admin/vouchers
Order ka status	PATCH /admin/orders/{id}/status
Gift request ki quote	POST /admin/custom-requests/{id}/quote
Express ghante, fees, cities	Render ke Variables, phir restart
Dashboard banne tak ye kaam kaise karoge
/docs page hi aapka temporary dashboard hai:

make admin phone=03xx... chala ke apne aap ko admin banao.
/docs kholo. otp/verify se login karo aur accessToken copy karo.
Upar Authorize button dabao aur token paste karo.
Ab koi bhi admin API form bhar ke chala sakte ho.
Production mein /docs band hota hai, kyunke ye secure tareeqa hai. Wahan ye kaam apne laptop wale backend se karo jo live database (Neon) se juda ho, ya kisi API tool (Postman, Bruno) se.

"Realtime" ke teen level
Level	Kya hota hai	Halat
1. Refresh par update	Screen kholte waqt, pull-to-refresh par, ya app wapis aane par naya data aata hai. Order screen har 30 second baad status check kar le	✅ Abhi ho sakta hai, free. React Query mein refetchInterval
2. Push notification	Order "Shipped" ho to phone par notification aaye	❌ Abhi nahi bana. Expo Push free hai. Backend mein device token save karne ki API aur status badalne par notification bhejna add karna hoga
3. Live (WebSocket)	Screen bina refresh ke khud badal jaye	Abhi zaroorat nahi. Render ke free server par ye theek se chalta bhi nahi
Shuru ke liye Level 1 + Level 2 kaafi hai. Bari apps bhi zyada tar yahi karti hain.

Kya backend se nahi badalta
Nayi screen, naya design ya button ki jagah. Ye app ka code hai, iske liye app update karni hi padegi. Home par kya dikhe (banners aur products) woh backend se control hota hai.

Main aage kya bana sakta hoon
Push notifications (Expo, free): device token save karne ki API, aur order status ya quote aane par notification.
App control settings: minAppVersion (purani app wale ko "update karo" dikhe) aur maintenanceMode (app ko kuch der band karne ka switch), /storefront/config mein.
Render deploy file (render.yaml): ek click mein deploy.
Batao kaun sa pehle karun? Mera mashwara hai ke 2 aur 3 pehle karo, kyunke dono chhote hain. Uske baad 1.