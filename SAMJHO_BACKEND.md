# Bazaura.pk Backend — Mukammal Samajh (Roman Urdu Guide)

> Ye file aapke samajhne ke liye hai. Isme bataya gaya hai ke repo me kya hai, har folder ka kaam kya hai,
> abhi kya missing hai, database kaun sa use karna hai, APIs kis order me banani hain aur deploy kahan karna hai.
> Basic Python aati hai to ye kaafi hai — baqi concepts yahan samjha diye gaye hain.

---

## 1. Big Picture — Ye backend karta kya hai?

Bazaura.pk ek ecommerce brand hai (men's clothes summer/winter, pants, perfumes waghera).
Iske do frontends honge:

1. **React Native app** (Android + iOS)
2. **Next.js website** (bazaura.pk)

Dono frontends **khud data store nahi karte**. Woh sirf screen dikhate hain. Asal data (products, users, orders)
**backend** ke paas hota hai. Frontend backend se internet ke zariye baat karta hai — isko **API** kehte hain.

```
 React Native App ─┐
                   ├──►  FastAPI Backend (Python)  ──►  PostgreSQL Database
 Next.js Website ──┘           │
                               ├──►  Redis (OTP / cache)       [optional shuru me]
                               └──►  Image Storage (R2 / S3)   [product photos]
```

**Misaal (Restaurant):**
- Frontend = waiter + menu card (customer ko dikhata hai)
- API = order lene ka counter (waiter yahan aa kar bolta hai "2 shirts ki list do")
- Backend = kitchen (asal kaam yahan hota hai)
- Database = store room (sara saman yahan para hai)

Ek hi backend dono frontends ko serve karega — isi liye isko achi tarah banana zaroori hai.

---

## 2. Repo ki abhi ki halat (Honest Status)

| Cheez | Status | Note |
| :--- | :--- | :--- |
| `app/core/` (config, database, security, redis) | ✅ Bana hua hai | Achi quality ka hai |
| `app/models/` (database tables) | ✅ Bana hua hai | Clothing ke liye thore changes chahiye (Section 6) |
| `app/schemas/` (request/response shapes) | ✅ Bana hua hai | |
| `app/services/` (business logic) | ⚠️ Adha | `pricing_service.py` me product ki jagah Voucher table query ho rahi hai aur price `1000` hardcode hai |
| `app/api/` (asal API endpoints) | ❌ **Missing** | Sab se bara kaam yahi hai |
| Root wali `main.py` | ❌ Bekaar | Isme sirf `hello` likha hai — delete kar dein |
| Alembic migrations | ❌ Missing | `alembic init` karna hai |
| `.env.example`, `Dockerfile`, `docker-compose.yml` | ❌ Missing | |
| Tests | ❌ Missing | |
| Payment code | 🗑️ **Hata diya gaya** | Detail Section 9 me |

> ⚠️ **Abhi app chalegi nahi.** `app/main.py` line 13 par `from app.api.v1 import router` hai, lekin `app/api/` folder
> exist hi nahi karta. Pehla kaam yahi folder banana hai (Section 7, Phase 0).

### Payment hatane me kya kya badla gaya
- `app/services/payment_service.py` — **delete** (JazzCash/EasyPaisa ka mock code tha)
- `app/services/__init__.py` — `PaymentService` ka import hata diya
- `app/core/config.py` — `JAZZCASH_*` aur `EASYPAISA_*` settings hata di
- `app/models/order.py` — `payment_method`, `payment_status`, `payment_reference` columns hata diye
- `app/schemas/order.py` — wohi teen fields hata diye
- `app/schemas/request.py` — `AcceptQuoteRequest` (jisme sirf payment_method tha) hata diya
- `backend_blueprint.md` — JazzCash/EasyPaisa sections, webhooks, payment fields hata diye

**Matlab:** Abhi har order **Cash on Delivery (COD)** samjha jayega. Pakistan me shuru me yahi sab se common hai.

---

## 3. Folder by Folder — Kis folder me kya hai aur kyun

```
python-bazaura-app-backend/
├── app/                      ← Sara asal code yahan
│   ├── main.py               ← App ka "start button"
│   ├── core/                 ← Bunyadi settings aur tools
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   └── redis.py
│   ├── models/               ← Database ki tables (store room ke shelves)
│   ├── schemas/              ← Data ki "shakal" jo frontend bhejta/leta hai
│   ├── services/             ← Business logic (hisaab kitaab)
│   └── api/  (abhi banana hai) ← Endpoints / URLs
├── backend_blueprint.md      ← Poori API ka naqsha (reference document)
├── requirements.txt          ← Python libraries ki list
└── SAMJHO_BACKEND.md         ← Ye file
```

### 3.1 `app/main.py` — Start button
Jab aap server chalate ho (`uvicorn app.main:app`), Python sab se pehle ye file chalata hai. Ye:
1. `FastAPI()` app banata hai
2. **CORS** lagata hai (ye allow karta hai ke Next.js site jo kisi aur domain par hai, backend ko call kar sake)
3. Saare API routers ko `/api/v1` ke neeche jorta hai
4. Startup par database tables bana deta hai aur Redis connect karta hai
5. `/health` endpoint deta hai — server zinda hai ya nahi check karne ke liye

Aur `/docs` par khud ba khud ek page ban jata hai jahan aap har API browser me test kar sakte ho (FastAPI ka kamaal).

### 3.2 `app/core/` — Bunyad

**`config.py`** — Saari settings ek jagah. Database ka password, secret key, delivery fee (Rs. 299 / Rs. 199),
free shipping limit (Rs. 10,000) waghera. Ye values `.env` file se parhta hai, taake password code me na likhne paren.

```python
settings.FREE_SHIPPING_THRESHOLD_PKR   # 10000
settings.async_database_url            # postgresql+asyncpg://user:pass@host/db
```

**`database.py`** — Database se connection banata hai.
- `engine` = database tak jane wali sarak
- `AsyncSessionLocal` = har request ke liye ek "session" (ek baat-cheet) kholta hai
- `get_db()` = har API ko ek session deta hai; kaam theek ho to `commit` (save), error aaye to `rollback` (sab wapis)

**`security.py`** — Login aur hifazat.
- `normalize_pakistan_phone("0300-1234567")` → `"+923001234567"` (har number ek hi format me save ho)
- `create_access_token()` — login ke baad user ko ek **JWT token** milta hai (jaise cinema ka ticket). Har request ke saath app ye ticket bhejti hai.
- `get_current_user` — ticket check karta hai aur batata hai kaun sa user hai
- `require_roles(["admin"])` — sirf admin ko andar aane do (dashboard ke liye kaam aayega)

**`redis.py`** — Redis ek bohot tez temporary memory hai. Yahan OTP codes (2 minute ke liye) aur cache rakhte hain.

### 3.3 `app/models/` — Database tables

Har class = database ki ek table. Har line = ek column. Ye **SQLAlchemy** library se banta hai.

```python
class Product(Base):
    __tablename__ = "products"
    title: Mapped[str] = mapped_column(String(255))   # column: title
    price: Mapped[int] = mapped_column(Integer)       # column: price (PKR me, integer)
```

| File | Tables | Kaam |
| :--- | :--- | :--- |
| `base.py` | — | ID banane ka function (`prod_a1b2c3...`) aur `created_at/updated_at` |
| `user.py` | `users`, `shipping_addresses` | Customer, admin ka data aur unke addresses |
| `product.py` | `categories`, `products`, `product_variants`, `product_reviews`, `vouchers` | Poora catalog |
| `order.py` | `orders`, `order_items`, `order_timeline` | Orders aur tracking steps |
| `request.py` | `custom_item_requests`, `sourcing_quotes` | "Request Item" feature (jo cheez store me nahi woh mangwao) |
| `content.py` | `editorial_content`, `wishlist_items` | Home screen banners/stories aur wishlist |

**Achi baat:** Order me `product_snapshot` aur `shipping_address_snapshot` save hota hai. Matlab agar kal shirt ki
price badal jaye, purane order me purani price hi dikhegi. Ecommerce me ye zaroori hai.

**Price integer me kyun?** `1999.99` jaisi decimal values computer me ghalat jama hoti hain. Rupees ko integer
(`1999`) me rakhna safe hai.

### 3.4 `app/schemas/` — Data ki shakal (Pydantic)

Model = database me kaise save hoga.
Schema = frontend ko kya bhejna/lena hai.

Dono alag kyun? Kyunke user table me `hashed_password` aur `role` hai — woh frontend ko **kabhi nahi bhejna**.
Schema decide karta hai ke kaun se fields bahar jayenge.

```python
class OTPRequest(BaseSchema):
    phone: str        # agar frontend phone na bheje to FastAPI khud error de dega
```

`base.py` me ek zabardast cheez hai: Python me `full_name` likho, JSON me khud `fullName` ban jata hai
(**camelCase**) — kyunke JavaScript (React Native / Next.js) me yahi style chalta hai.

Har response ek hi shakal me jata hai:
```json
{ "success": true, "message": "...", "data": { ... } }
```
Frontend developers ke liye ye bohot asaan hai.

### 3.5 `app/services/` — Business logic

Yahan woh "dimagh wala" kaam hota hai jo API se alag rakhna behtar hai:

| File | Kaam |
| :--- | :--- |
| `pricing_service.py` | Cart ka total: subtotal − voucher discount + delivery fee. ⚠️ Abhi products ko theek se database se nahi uthata — fix karna hai |
| `notification_service.py` | SMS aur push notification (abhi sirf log likhta hai, asal me bhejta nahi) |
| `s3_service.py` | Image upload ke liye "presigned URL" — app seedha storage par photo upload karti hai, backend par bojh nahi parta |

### 3.6 `app/api/v1/` — Endpoints (abhi banana hai)

Ye woh URLs hain jo frontend call karega. Har file me ek `APIRouter` hoga:

```python
# app/api/v1/products.py
router = APIRouter(prefix="/products", tags=["Products"])

@router.get("")
async def list_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.in_stock == True))
    return ApiResponse(data=result.scalars().all())
```

Aur `app/api/v1/__init__.py` sab routers ko jor kar ek `router` banata hai jo `main.py` import karta hai.

---

## 4. Ek request ka safar (step by step)

Customer app me "Shirts" category kholta hai:

```
1. App bhejti hai:      GET https://api.bazaura.pk/api/v1/products?category_id=cat_shirts
2. main.py:             request ko products router tak bhejta hai
3. api/v1/products.py:  get_db() se database session leta hai
4. models/product.py:   SQLAlchemy SQL query banata hai → PostgreSQL se shirts aati hain
5. schemas/product.py:  data ko ProductResponse ki shakal me dhaalta hai (camelCase)
6. Response:            { "success": true, "data": { "items": [...], "pagination": {...} } }
7. App:                 screen par shirts dikha deti hai
```

Agar login wali API ho (jaise "mere orders"), to step 3 se pehle `get_current_user` token check karta hai.

---

## 5. Database — Kaun sa aur kyun?

### ✅ Recommendation: **PostgreSQL**

Code pehle se PostgreSQL ke liye likha hua hai (`asyncpg` driver). Iske faide:
- Ecommerce ke liye perfect — orders me **transactions** chahiye (stock kam ho aur order bane, dono ek saath, ya dono na hon)
- `JSON` columns support karta hai (product images, variants, specifications)
- Free hosting bohot jagah milti hai
- Mustaqbil me dashboard / reports ke liye SQL queries bohot powerful hain

**MongoDB kyun nahi?** Ho sakta hai, lekin saara code SQLAlchemy (SQL) par likha hai. Badalna matlab sab dobara likhna. Zaroorat nahi.

### Kahan host karein?

| Kaam | Option | Kyun |
| :--- | :--- | :--- |
| Local development | Docker me Postgres **ya** Postgres.app (Mac) | Apne laptop par free |
| Production DB | **Neon** ya **Supabase** | Managed Postgres, free tier se shuru, backups khud |

### Redis — Abhi zaroori hai?
- Shuru me **zaroori nahi**. OTP codes database table me bhi rakh sakte hain.
- Jab chahiye ho (rate limiting, caching), **Upstash Redis** ka free tier le lein.
- **Celery** (background workers) bhi abhi hata kar rakhein. FastAPI ka built-in `BackgroundTasks` shuru ke liye kaafi hai.

### Migrations (Alembic) — Ye kya hai?
Jab aap model me naya column jorte ho (jaise `fabric`), database ko bhi batana parta hai.
**Alembic** ye kaam karta hai — har change ki ek "migration" file banti hai, jaise git commits database ke liye.

```bash
alembic revision --autogenerate -m "add fabric to products"   # change detect karo
alembic upgrade head                                          # database par lagao
```
`main.py` me jo `create_all` hai woh sirf naye tables banata hai, purani tables me column nahi jorta. Production me Alembic hi use karein.

---

## 6. Bazaura.pk (clothing + perfume) ke liye kya badalna chahiye

`backend_blueprint.md` kisi **electronics / quick-commerce** app ke liye likha gaya tha (iPhone, PS5 examples).
Bazaura clothing brand hai, to ye changes karne chahiye:

### 6.1 Product me naye fields
| Field | Example | Kyun |
| :--- | :--- | :--- |
| `slug` | `black-cotton-kurta-summer` | Next.js website ke URLs aur Google SEO ke liye **bohot zaroori** |
| `gender` | `MEN`, `WOMEN`, `UNISEX` | Filter ke liye |
| `season` | `SUMMER`, `WINTER`, `ALL_SEASON` | Summer/winter collection |
| `fabric` | `Cotton`, `Lawn`, `Wool`, `Khaddar` | Kapron ke liye aham |
| `size_chart_url` | image link | Customer size samajh sake |
| `is_active` | `true/false` | Product chupane ke liye (delete kiye baghair) |

### 6.2 Variants aur stock — sab se aham change
Abhi stock **poore product** par hai (`stock_count`). Lekin kapron me stock **har size + color** ka alag hota hai:
"Black shirt, size M" — 5 piece, "Black shirt, size XL" — 0 piece.

Is liye ek nayi table `product_skus` banayein:
```
product_skus: id, product_id, size, color, sku_code, stock_count, price_modifier
```
Order karte waqt isi SKU ka stock kam hoga. Perfume me variants `50ml / 100ml` honge — wahi table kaam karegi.

### 6.3 Ye features rakhne hain ya nahi? (aap decide karein)
- **Lahore 2-hour express delivery** — Bazaura ye deta hai? Agar nahi, to sirf ek "standard delivery" rakhein.
- **Sourcing Concierge / Request Item** (`request.py`) — ye electronics ke liye tha. Clothing me shayad zaroorat na ho.
  Na chahiye to model, schema aur endpoints na banayein.

---

## 7. Roadmap — Backend step by step kaise tayar karein

Har phase ke baad `/docs` par test karein, phir agla phase.

### Phase 0 — App ko chalne layak banana (1-2 din)
1. Root wali `main.py` (`hello`) delete
2. `app/api/__init__.py` aur `app/api/v1/__init__.py` banana (khali router ke saath)
3. `.env.example` banana (DB URL, SECRET_KEY)
4. `docker-compose.yml` — local Postgres (aur zaroorat ho to Redis)
5. `alembic init migrations` aur pehli migration
6. Server chalana: `uvicorn app.main:app --reload` → `http://localhost:8000/docs` khulna chahiye

### Phase 1 — Catalog (sab se pehle, kyunke bina login ke dikhta hai)
| Method | URL | Kaam |
| :--- | :--- | :--- |
| GET | `/api/v1/categories` | Saari categories |
| GET | `/api/v1/products` | List + search + filter (category, gender, season, price) + sort + pagination |
| GET | `/api/v1/products/{id_or_slug}` | Ek product ki detail (variants, reviews) |
| GET | `/api/v1/content/home` | Home screen ka sara data ek call me |

Saath me ek **seed script** (`scripts/seed.py`) jo test products database me daal de.

### Phase 2 — Login aur profile
| Method | URL | Kaam |
| :--- | :--- | :--- |
| POST | `/api/v1/auth/otp/request` | Phone par OTP bhejo |
| POST | `/api/v1/auth/otp/verify` | OTP check, token do (naya user ho to bana do) |
| POST | `/api/v1/auth/refresh` | Naya token |
| GET/PUT | `/api/v1/users/me` | Profile dekho / badlo |
| POST/DELETE | `/api/v1/users/me/addresses` | Addresses |

> 💡 SMS OTP ke paise lagte hain. Development me OTP console me print karwa lein (`notification_service` already yahi karta hai).
> Production me Pakistani SMS provider ya Firebase Phone Auth.

### Phase 3 — Cart aur Orders (COD)
| Method | URL | Kaam |
| :--- | :--- | :--- |
| POST | `/api/v1/cart/validate` | Total, discount, delivery fee calculate (pricing_service fix karke) |
| POST | `/api/v1/orders` | Order banao — stock kam karo, snapshot save karo, timeline banao |
| GET | `/api/v1/orders` | Mere orders |
| GET | `/api/v1/orders/{id}` | Order detail + tracking |
| POST | `/api/v1/orders/{id}/cancel` | Order cancel (sirf jab tak dispatch na hua ho) |

⚠️ **Zaroori rule:** Price kabhi frontend se trust na karein. Frontend sirf `product_id` aur `quantity` bheje,
price backend database se khud uthaye. Warna koi bhi Rs. 1 me shirt order kar dega.

### Phase 4 — Baqi features
- `/api/v1/wishlist` (GET, POST toggle)
- `/api/v1/products/{id}/reviews` (POST — sirf jisne kharida ho)
- `/api/v1/uploads/presigned-url` (profile photo)
- Order status badalne par SMS/push notification

### Phase 5 — Admin APIs (dashboard ki tayari)
Dashboard abhi nahi banana, lekin uski APIs yahin banengi. `require_roles(["admin"])` pehle se `security.py` me hai.
- Products/categories/vouchers ka CRUD (create, read, update, delete)
- Orders list + status change (`CONFIRMED` → `SHIPPED` → `DELIVERED`)
- Simple stats (aaj ke orders, total sale)

Baad me Next.js me hi `/admin` pages bana kar inhi APIs ko call kar lena — alag backend ki zaroorat nahi.

### Har phase ke saath
- `tests/` folder me `pytest` tests (kam az kam har API ka ek "happy path" test)
- CORS me `"*"` ki jagah asal domains: `https://bazaura.pk`, `http://localhost:3000`
- `SECRET_KEY` sirf `.env` se aaye — code me jo default likha hai woh production me **kabhi** use na ho

---

## 8. Deploy kahan karein

### Recommended setup (shuru ke liye — sasta aur asaan)

| Cheez | Kahan | Note |
| :--- | :--- | :--- |
| FastAPI backend | **Railway** ya **Render** | GitHub connect karo, push karte hi deploy. `Dockerfile` chahiye hoga |
| PostgreSQL | **Neon** ya **Supabase** | Free tier se shuru |
| Product images | **Cloudflare R2** ya **Cloudinary** | R2 S3-compatible hai (`s3_service.py` thore change se chal jayega). Cloudinary khud images resize karta hai |
| Next.js website | **Vercel** | Next.js ke banane walon ka apna platform |
| React Native app | Expo EAS → Play Store / App Store | |
| Domain | `api.bazaura.pk` → backend, `bazaura.pk` → Vercel | |

### Jab traffic barh jaye
Ek **VPS** (DigitalOcean / Hetzner / AWS Lightsail) par Docker ke saath khud chalayein — mahine ka kharcha
fixed aur kam hota hai, lekin server ki dekh bhaal khud karni parti hai.

### Deploy ka flow
```
Code likha → git push → Railway/Render khud build karega → alembic upgrade head → live
```

---

## 9. Payment — baad me kaise wapis aayegi

Abhi saara payment code hata diya gaya hai aur har order COD hai. Jab online payment chahiye ho:
1. `orders` table me dobara `payment_method`, `payment_status`, `payment_reference` columns (Alembic migration ke zariye)
2. `app/services/payment_service.py` — asal gateway (JazzCash / EasyPaisa / Safepay / PayFast) ka SDK
3. `app/api/v1/webhooks.py` — gateway payment hone par backend ko khud batata hai; uska **signature verify karna zaroori hai**
4. Order tab tak `PENDING_PAYMENT` rahe jab tak webhook na aaye

Purana mock code git history me hai (commit `065f395`) agar reference chahiye ho.

---

## 10. Chhoti chhoti cheezein jo baad me theek karni hain

- `app/main.py` me `@app.on_event("startup")` purana tareeqa hai — naya tareeqa `lifespan` hai (abhi chalta hai, sirf warning)
- `models/request.py` me `datetime.utcnow` — `datetime.now(timezone.utc)` hona chahiye
- `passlib` library ab maintain nahi hoti; OTP login me password ki zaroorat hi nahi, to shayad hata dein
- `s3_service.py` me `endpoint_url="http://localhost:9000"` hardcode hai — `.env` se aana chahiye

---

## 11. Mushkil alfaaz ki dictionary

| Lafz | Matlab |
| :--- | :--- |
| **API** | Frontend aur backend ke beech baat karne ka tareeqa (URLs) |
| **Endpoint** | Ek specific URL + method, jaise `GET /products` |
| **GET / POST / PUT / DELETE** | Data lena / naya banana / badalna / mitana |
| **FastAPI** | Python ka framework jisse APIs banti hain |
| **ORM (SQLAlchemy)** | SQL likhe baghair Python classes se database chalana |
| **Pydantic** | Data check karne wali library (phone khali to nahi, quantity 0 se zyada hai) |
| **JWT Token** | Login ke baad milne wala digital ticket |
| **OTP** | Phone par aane wala ek baar ka code |
| **CORS** | Browser ki security; batata hai kaun se websites backend call kar sakti hain |
| **Migration** | Database ki structure me change ka record |
| **async / await** | Ek request database ka intezar kare to server dusri requests sambhal le — server tez chalta hai |
| **Environment variables (.env)** | Passwords/settings jo code ke bahar rakhe jaate hain |
| **Seed data** | Testing ke liye database me dala gaya nakli data |
| **SKU** | Har size/color combination ka alag code jiska apna stock hota hai |

---

**Agla qadam:** Phase 0 shuru karein — `app/api/v1/` banayein taake server chal sake aur `/docs` khul jaye.
