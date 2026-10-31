# Bazaura.pk Backend — Mukammal Guide (Roman Urdu)

> Ye guide aapke liye hai. Isme bataya gaya hai ke backend kaise bana hai, har folder aur file kya karti hai,
> ek request kaise chalti hai, aapko khud kya kya karna hai, aur deploy kaise hoga.
> Basic Python kaafi hai — baqi har concept yahan samjhaya gaya hai.

---

## 1. Big picture

Bazaura.pk ek clothing brand hai (hoodies, jackets, shirts, trousers, tracksuits, pants). Baad me aur cheezein
(perfume waghera) bhi aa sakti hain — backend isi hisaab se banaya gaya hai.

```
 React Native App ─┐
                   ├──►  FastAPI Backend (ye repo)  ──►  PostgreSQL Database
 Next.js Website ──┘           │
                               ├──►  SMS provider (OTP login)
                               └──►  Image storage (Cloudflare R2 / S3)
```

- **Frontend** (app + website) sirf screen dikhata hai.
- **Backend** asal kaam karta hai: products dikhana, login, cart ka hisaab, order banana, stock kam karna.
- **Database** me sab data hamesha ke liye save hota hai.
- Dono frontends **ek hi backend** use karte hain.

**Payment:** Abhi koi online payment nahi. Har order **Cash on Delivery (COD)** hai.

---

## 2. Abhi kya tayar hai

| Cheez | Status |
| :--- | :--- |
| 63 API endpoints (customer + admin) | ✅ |
| Phone + OTP login (JWT tokens) | ✅ |
| Clothing catalog: size/color ka alag stock, filters, search, sorting | ✅ |
| Cart pricing, vouchers, standard + express delivery | ✅ |
| Orders (COD), stock reserve, cancel par stock wapis, tracking timeline | ✅ |
| Custom requests: "ye cheez arrange karo" + "kisi ko gift bhejo" | ✅ |
| Wishlist, reviews (verified purchase badge) | ✅ |
| SEO data (slug, meta title/description, canonical URL, sitemap) | ✅ |
| Admin/staff APIs (dashboard ke liye tayar) | ✅ |
| Database migrations (Alembic) | ✅ |
| 34 automated tests | ✅ sab pass |
| Docker, CI (GitHub Actions), Makefile | ✅ |
| Asal SMS bhejna | ❌ Aapko provider chunna hai (Section 9) |
| Online payment, push notifications, dashboard UI | ⏳ Baad me |

---

## 3. Express delivery — 3 ghante (badalna asaan hai)

Express delivery abhi **3 ghante** ki hai, aur sirf **Lahore** me. Ye number code me kahin "hard-coded" nahi hai.
Ye `.env` file me ek setting hai:

```
EXPRESS_DELIVERY_HOURS=3
EXPRESS_DELIVERY_CITIES=["Lahore"]
EXPRESS_DELIVERY_FEE_PKR=299
STANDARD_DELIVERY_FEE_PKR=199
FREE_SHIPPING_THRESHOLD_PKR=10000
```

Kal 2 ghante karna ho, ya Karachi add karna ho → bas ye value badlo aur server restart karo. Code nahi chhedna.

Frontend bhi ye number khud nahi likhta — woh `GET /api/v1/storefront/config` se poochta hai.
Is liye app aur website par bhi "3 hours" khud badal jayega.

> **Professional rule:** Jo business values badal sakti hain (fees, ghante, cities), woh config me rehti hain, code me nahi.

---

## 4. Folder structure — kis folder me kya hai

```
python-bazaura-app-backend/
├── app/                    ← Saara asal code
│   ├── main.py             ← App ka "start button"
│   ├── core/               ← Bunyadi cheezein (settings, database, security, errors)
│   ├── models/             ← Database ki tables
│   ├── schemas/            ← Frontend ke saath data ki "shakal"
│   ├── services/           ← Business logic (dimagh)
│   ├── api/                ← URLs / endpoints (darwaze)
│   │   ├── deps.py         ← Login check, admin check, pagination
│   │   └── v1/             ← Version 1 ki saari APIs
│   │       └── admin/      ← Sirf staff/admin ki APIs
│   └── utils/              ← Chhote helper functions
├── migrations/             ← Database ke changes ka record (Alembic)
├── scripts/                ← Seed data aur admin banane ke scripts
├── tests/                  ← Automated tests
├── docs/                   ← Ye guide + API reference
├── .github/workflows/      ← CI: har push par tests khud chalte hain
├── Dockerfile              ← Server par chalane ka "dabba"
├── docker-compose.yml      ← Laptop par Postgres + API ek command se
├── Makefile                ← Chhote commands (make dev, make test ...)
├── requirements.txt        ← Production ki libraries
├── requirements-dev.txt    ← Development/testing ki libraries
├── pyproject.toml          ← Tools ki settings (pytest, ruff)
├── alembic.ini             ← Migrations ki settings
├── .env.example            ← Settings ka template (copy karke .env banao)
└── README.md               ← Developers ke liye short intro (English)
```

**Restaurant ki misaal yaad rakhein:**
- `api/` = waiter (order leta hai, jawab deta hai)
- `services/` = chef (asal kaam aur hisaab)
- `models/` = store room ke shelves (database tables)
- `schemas/` = menu card aur order slip (kya aa sakta hai, kya jayega)
- `core/` = restaurant ke rules aur bijli-paani

### 4.1 `app/core/`

| File | Kaam |
| :--- | :--- |
| `config.py` | **Saari settings.** `.env` se values parhta hai. Production me ghalat settings (kamzor SECRET_KEY) par app chalne se inkaar kar deta hai. |
| `database.py` | Database connection aur har request ke liye ek "session". |
| `security.py` | JWT token banana/check karna, OTP ko hash karna, Pakistani phone number theek format me lana (`0300-1234567` → `+923001234567`). |
| `exceptions.py` | Errors ki qismein (`NotFoundError`, `ConflictError` ...) aur unko ek jaisa JSON jawab banana. |

### 4.2 `app/models/` — database tables

| File | Tables | Kaam |
| :--- | :--- | :--- |
| `base.py` | — | ID banana (`prd_9f2c…`), `created_at/updated_at`, UTC time |
| `enums.py` | — | Allowed values: order status, gender, season, delivery type ... |
| `user.py` | `users`, `addresses`, `otp_codes` | Customers/staff, unke addresses, login codes |
| `catalog.py` | `categories`, `products`, `product_variants`, `product_reviews` | Poora catalog |
| `voucher.py` | `vouchers` | Promo codes (WELCOME10) |
| `order.py` | `orders`, `order_items`, `order_status_events` | Orders, unki cheezein, status history |
| `custom_request.py` | `custom_requests`, `custom_request_quotes` | Arrange/gift requests aur unki quotes |
| `content.py` | `content_blocks` | Home screen banners/stories |
| `wishlist.py` | `wishlist_items` | Wishlist |

**Kapron ke liye sab se aham design — Variants:**

Ek product = "Classic Black Hoodie". Lekin bikta hai **variant**: "Black, size M".
Har variant ka apna **SKU** aur apna **stock** hai:

```
Product: Classic Pullover Hoodie (Rs. 3,499)
 ├── Variant: Black / S   → SKU CPH-BLA-S   → stock 10
 ├── Variant: Black / M   → SKU CPH-BLA-M   → stock 4
 └── Variant: Grey  / XL  → SKU CPH-GRE-XL  → stock 0  (out of stock)
```

Perfume aaye to `size` me `100ml` likh do — wohi table kaam karegi.

**Categories nested hain:** `Men → Hoodies`. "Men" kholo to hoodies, jackets sab aa jate hain.

**Snapshot:** Order me product ka naam, price, size aur address **copy** ho kar save hota hai.
Kal price badle ya customer address edit kare, purana order waisa hi rahega.

### 4.3 `app/schemas/` — data ki shakal

Model = database me kaise save hota hai. Schema = frontend ko kya bhejna/lena hai.
Misal: user table me `role` hai, lekin public profile me sirf zaroori cheezein jati hain.

- Python me `full_name`, JSON me khud `fullName` (camelCase) — JavaScript ka style.
- Har jawab ek hi shakal me:
  ```json
  { "success": true, "message": "Order placed", "data": { ... } }
  ```
- Error bhi ek hi shakal me:
  ```json
  { "success": false, "message": "Incorrect code", "error": { "code": "OTP_INVALID", "details": null } }
  ```
  Frontend `error.code` dekh kar faisla karta hai (jaise `TOKEN_EXPIRED` → naya token lo).

| File | Kya hai |
| :--- | :--- |
| `common.py` | Base schema, `ApiResponse`, pagination |
| `validators.py` | Phone number ki khud-ba-khud jaanch |
| `auth.py`, `user.py` | Login, profile, address |
| `catalog.py` | Product card, product detail (SEO ke saath), category, review |
| `cart.py` | Cart quote |
| `order.py` | Order banana/dikhana, timeline |
| `custom_request.py` | Arrange/gift requests |
| `storefront.py` | Home feed, config, sitemap, uploads |
| `admin.py` | Admin ke create/update forms |

### 4.4 `app/services/` — dimagh

| File | Kaam |
| :--- | :--- |
| `auth_service.py` | OTP bhejna (60 sec ka gap, 15 min me 3 baar), check karna (5 ghalat koshishon par lock), naya account banana, tokens dena |
| `catalog_service.py` | Product search/filter/sort, category tree, unique slug banana |
| `pricing_service.py` | **Cart ka asal hisaab** — price database se, stock check, voucher, delivery fee. Cart screen aur order dono yahi use karte hain, is liye jo customer dekhta hai wohi charge hota hai |
| `delivery.py` | Delivery options, fee, "Delivered within 3 hours" wala text |
| `order_service.py` | Order banana (stock kam), cancel (stock wapis), status aage barhana (sirf allowed steps), timeline |
| `custom_request_service.py` | Request → quote → accept → order |
| `notification_service.py` | SMS (abhi sirf console me print) |
| `storage_service.py` | Image upload ke liye presigned URL |

### 4.5 `app/api/` — darwaze (endpoints)

`deps.py` me teen "chowkidar" hain:
- `CurrentUser` — login zaroori
- `StaffUser` — staff ya admin
- `AdminUser` — sirf admin

Route me bas likh do, check khud ho jata hai:
```python
@router.post("/orders")
async def place_order(payload: OrderCreate, user: CurrentUser, db: DbSession):
    order = await order_service.place_order(db, user, payload)
    return ApiResponse(message="Order placed", data=order_service.to_order_out(order))
```
Route **patla** rehta hai — asal kaam service karti hai. Ye professional teams ka standard hai.

---

## 5. Ek order ka safar (step by step)

1. App cart dikhane se pehle bhejti hai `POST /cart/quote` → backend live price, stock, voucher, delivery fee batata hai.
2. Customer "Place order" dabata hai → `POST /orders` me sirf `variantId`, `quantity`, `addressId` jata hai.
   **Price frontend se kabhi nahi liya jata** — warna koi bhi Rs. 1 me hoodie order kar dega.
3. `order_service.place_order`:
   - address check (kya ye isi user ka hai?)
   - `pricing_service` se dobara hisaab, variants ko **lock** karke (do log aakhri piece ek saath na le sakein)
   - koi masla (stock khatam) → `400 CART_INVALID` + masle ki list
   - sab theek → stock kam, order + items + "PLACED" status save, voucher ka use count +1
   - sab kuch **ek transaction** me: ya poora hoga, ya kuch bhi nahi
4. Staff dashboard se status aage karta hai: `PLACED → CONFIRMED → PACKED → SHIPPED → DELIVERED`.
   Ghalat jump (PLACED → DELIVERED) allowed nahi.
5. Customer `CONFIRMED` tak cancel kar sakta hai → stock khud wapis.

## 6. Custom request / gift ka safar

1. Customer `POST /custom-requests` — `requestType: "GIFT"`, cheez ka naam, recipient ka address, gift message,
   gift wrap, "mera naam na batana" (`hideSender`).
2. Staff dekhta hai → `POST /admin/custom-requests/{id}/quote` me ek piece ki price (`unitPrice`) deta hai.
   Delivery fee aur gift wrap fee khud lag jati hai.
3. Customer app me quote dekhta hai → `accept-quote` → ek normal **COD order** ban jata hai.
4. Quote 2 din me expire hoti hai (setting se badal sakte hain).

---

## 7. SEO (website ke liye)

Har product aur category ke saath backend ye deta hai:
- `slug` → URL: `bazaura.pk/product/classic-pullover-hoodie`
- `seo.title`, `seo.description`, `seo.canonicalUrl`, `seo.image` → Google aur social media ke liye
- `breadcrumbs` → "Men › Hoodies"
- `GET /seo/sitemap` → saare URLs; Next.js isse `sitemap.xml` banata hai

Admin chahe to har product ka `metaTitle` / `metaDescription` khud likh sakta hai; khali chhode to backend
title/description se khud bana deta hai.

Next.js developer ko bolna: product/category pages **server-side render** karein aur JSON-LD (Product + Breadcrumb) lagayein.
Detail `docs/API_REFERENCE.md` me hai.

---

## 8. Laptop par kaise chalayein

Pehli baar:
```bash
make install                 # .venv banata hai, libraries install karta hai
cp .env.example .env         # settings file
```

Database ke do raaste:
- **Docker ho to:** `make db` (Postgres laptop par chal jayega)
- **Docker na ho to:** neon.tech par free Postgres banao, uska URL `.env` me `DATABASE_URL` me daalo
  (shuru me `postgresql://` ko `postgresql+asyncpg://` kar dena, aur aakhir me `?sslmode=require` ho to
  usko `?ssl=require` kar dena — asyncpg driver `sslmode` nahi samajhta)

Phir:
```bash
make migrate                                  # tables banao
make seed                                     # 10 sample products
make admin phone=03001234567 name="Umer"      # apne aap ko admin banao
make dev                                      # server chalao
```

Browser me kholo: **http://localhost:8000/docs** — har API yahin test ho sakti hai.
Login karte waqt OTP `123456` hoga (sirf development me, `.env` ki `OTP_FIXED_CODE` se).

Roz ke commands:

| Kaam | Command |
| :--- | :--- |
| Server chalana | `make dev` |
| Tests chalana | `make test` |
| Code saaf karna | `make format` |
| Model me naya column jora | `make migration m="add xyz"` phir `make migrate` |

---

## 9. ✅ Aapko khud kya karna hai (checklist)

Ye kaam code se nahi hote — business ke faisle ya accounts hain:

**Abhi (development ke liye):**
- [ ] `make install` chala ke `http://localhost:8000/docs` khol ke dekhein
- [ ] Neon (ya Docker) par database banayein
- [ ] Apni fees confirm karein: standard Rs. 199, express Rs. 299, free delivery Rs. 10,000 se — ghalat ho to `.env` me badlein
- [ ] Express sirf Lahore me? Aur cities hon to `EXPRESS_DELIVERY_CITIES` me daalein
- [ ] Frontend developers ko `docs/API_REFERENCE.md` aur `/docs` ka link dein

**Launch se pehle:**
- [ ] **SMS provider chunein** (OTP ke liye) — koi Pakistani SMS gateway ya Twilio. Uski API key milne par
      `app/services/notification_service.py` me `_send_via_provider` likhna hoga (chhota sa kaam)
- [ ] **Cloudflare R2** (ya AWS S3) par bucket banayein — product photos ke liye. Keys `.env` ke `STORAGE_*` me
- [ ] **Railway** ya **Render** par account (backend deploy ke liye)
- [ ] Domain: `api.bazaura.pk` backend ke liye, `bazaura.pk` website (Vercel) ke liye
- [ ] Production ka `SECRET_KEY` banayein: `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- [ ] Asal products, photos, size charts admin APIs (ya baad me dashboard) se daalein
- [ ] Privacy policy / return policy (Play Store aur App Store maangte hain)

---

## 10. Deploy kaise hoga

| Cheez | Kahan | Kyun |
| :--- | :--- | :--- |
| Backend | **Railway** ya **Render** | GitHub connect karo; `Dockerfile` khud detect hota hai |
| Database | **Neon** (ya Supabase) | Managed Postgres, backups khud |
| Images | **Cloudflare R2** | S3 jaisa, sasta, data bahar bhejne ki fees nahi |
| Website | **Vercel** | Next.js ke liye best |
| App | Expo EAS → Play Store / App Store | |

Deploy ka flow:
```
git push → Railway Docker image banata hai → container start par khud `alembic upgrade head` (tables update)
→ server live → https://api.bazaura.pk/health par {"status":"ok"}
```

Production me ye settings zaroor lagani hain (Railway ke "Variables" me):
```
ENVIRONMENT=production
SECRET_KEY=<lamba random>
DATABASE_URL=<Neon ka URL, postgresql+asyncpg:// ke saath>
CORS_ORIGINS=["https://bazaura.pk","https://www.bazaura.pk"]
SITE_URL=https://bazaura.pk
SMS_PROVIDER=<aapka provider>
STORAGE_...=<R2 keys>
```
`ENVIRONMENT=production` hone par `/docs` band ho jata hai, kamzor SECRET_KEY par app start nahi hoti,
aur `OTP_FIXED_CODE` allowed nahi — ye hifazat ke liye hai.

**CI:** Har `git push` par GitHub khud lint, migrations (asal Postgres par) aur saare tests chalata hai.
Laal ❌ aaye to merge na karein.

---

## 11. Baad me kya add hoga

| Feature | Kahan add hoga |
| :--- | :--- |
| **Online payment** (JazzCash/EasyPaisa/Safepay) | `orders` me `payment_method/payment_status` columns (migration), `services/payment_service.py`, `api/v1/webhooks.py` (signature verify zaroori) |
| **Push notifications** | User ka device token save karna + `notification_service` me FCM |
| **Admin dashboard** | APIs tayar hain (`/api/v1/admin/...`). Next.js me `/admin` pages bana kar inhi ko call karna |
| **Nayi categories** (perfume) | Kuch nahi badalna — nayi category banao, variant me `size=100ml` |
| **Rate limiting / caching** | Jab traffic barhe, Redis (Upstash) add karna |

---

## 12. Mushkil alfaaz

| Lafz | Matlab |
| :--- | :--- |
| **API / Endpoint** | Frontend aur backend ke beech baat ka tareeqa; ek URL + method (`GET /products`) |
| **GET / POST / PATCH / PUT / DELETE** | Lena / banana / thora badalna / rakhna (idempotent) / mitana |
| **FastAPI** | Python framework jisse APIs banti hain; `/docs` khud banata hai |
| **SQLAlchemy (ORM)** | SQL likhe baghair Python classes se database chalana |
| **Pydantic** | Data ki jaanch (phone sahi hai? quantity 1 se zyada?) |
| **Alembic / Migration** | Database ki structure me har change ka record — git jaisa, lekin tables ke liye |
| **JWT / Access token** | Login ke baad ka digital ticket (1 ghanta). **Refresh token** se naya ticket (30 din) |
| **OTP** | Phone par aane wala ek baar ka code |
| **Variant / SKU** | Ek size + color ka combination, jiska apna code aur stock hai |
| **Slug** | URL wala naam: `classic-pullover-hoodie` |
| **Transaction** | Kai database kaam jo ya sab honge ya koi nahi |
| **Idempotent** | Do baar karo ya ek baar, nateeja same (wishlist me add) |
| **CORS** | Browser ki security: kaun si websites backend call kar sakti hain |
| **CI** | Har push par khud tests chalne ka system |
| **Docker** | App ko ek "dabbe" me band karna jo har server par ek jaisa chale |
| **async / await** | Database ka intezar karte hue server dusri requests sambhal leta hai |
