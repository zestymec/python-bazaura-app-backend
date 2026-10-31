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
