# Bazaura.pk API Reference (v1)

Base URL: `https://api.bazaura.pk/api/v1` (local: `http://localhost:8000/api/v1`)

The interactive OpenAPI docs at `/docs` are the source of truth for exact request and response fields.
This page explains how the pieces fit together.

## Conventions

| Topic | Rule |
| --- | --- |
| Auth | `Authorization: Bearer <accessToken>` |
| Casing | JSON keys are camelCase. Requests also accept snake_case. |
| Success | `{"success": true, "message": "...", "data": {...}}` |
| Error | `{"success": false, "message": "...", "error": {"code": "CART_INVALID", "details": [...]}}` |
| Pagination | `?page=1&limit=20` → `data: {"items": [...], "meta": {"page", "limit", "totalItems", "totalPages"}}` |
| Money | Integers in PKR |
| Dates | ISO-8601, UTC |
| Payment | Every order is Cash on Delivery (`paymentMethod: "CASH_ON_DELIVERY"`) |

Common error codes: `VALIDATION_ERROR` (422), `AUTH_REQUIRED` / `TOKEN_EXPIRED` (401 — call `/auth/refresh`),
`INSUFFICIENT_ROLE` (403), `*_NOT_FOUND` (404), `*_NOT_CANCELLABLE` / `INVALID_STATUS_TRANSITION` (409),
`OTP_COOLDOWN` / `OTP_RATE_LIMITED` (429).

## Auth

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/auth/otp/request` | – | Send a 6-digit code by SMS. `{ phone }` |
| POST | `/auth/otp/verify` | – | `{ phone, code, fullName? }` → tokens, `user`, `isNewUser` |
| POST | `/auth/refresh` | – | `{ refreshToken }` → new token pair |

Phones are accepted as `03001234567`, `+92 300 1234567`, etc. and stored as `+923001234567`.
Limits: 60 s between codes, 3 codes per 15 min, 5 wrong attempts per code, codes expire after 5 min.

## Account

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/users/me` | user | Profile + addresses |
| PATCH | `/users/me` | user | `fullName`, `email`, `avatarUrl`, `city` |
| GET | `/users/me/addresses` | user | Saved addresses (default first). Each has `isExpressEligible` |
| POST | `/users/me/addresses` | user | Add (first address becomes default; max 10) |
| PATCH | `/users/me/addresses/{id}` | user | Edit / set `isDefault: true` |
| DELETE | `/users/me/addresses/{id}` | user | Delete (default moves to the next address) |

## Catalog

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/categories` | – | Category tree (`children` nested) |
| GET | `/categories/{slug}` | – | Category page: breadcrumbs, children, `seo` |
| GET | `/products` | – | Listing with filters (below) |
| GET | `/products/{slug}` | – | Product page: variants, breadcrumbs, `seo` (slug or id accepted) |
| GET | `/products/{slug}/related` | – | Related products |
| GET | `/products/{slug}/reviews` | – | Published reviews (paginated) |
| POST | `/products/{slug}/reviews` | user | One review per customer; verified if they received the product |

`GET /products` query parameters:

| Param | Example | Notes |
| --- | --- | --- |
| `category` | `men-hoodies` | Includes sub-categories |
| `gender` | `MEN` | Also returns `UNISEX` |
| `season` | `WINTER` | `SUMMER`, `WINTER`, `ALL_SEASON` |
| `size`, `color` | `size=M&size=L` | Repeatable; only in-stock variants match |
| `minPrice`, `maxPrice` | `5000` | PKR |
| `q` | `fleece` | Searches title, brand, fabric, tags |
| `express`, `inStock`, `onSale`, `featured` | `true` | Boolean filters |
| `sort` | `newest` | `newest`, `popular`, `price_asc`, `price_desc`, `rating` |

Products are sold by **variant** (one size + colour). Use `variants[].id` when adding to the cart.

## Cart & checkout

The cart is stored on the device. Price it on the server whenever it changes:

`POST /cart/quote` (guests allowed)
```json
{ "items": [{ "variantId": "var_…", "quantity": 2 }], "voucherCode": "WELCOME10", "deliveryType": "EXPRESS", "city": "Lahore" }
```
Returns lines with live prices and stock, `subtotal`, `discount`, `deliveryFee`, `total`, `deliveryOptions`,
`amountToFreeShipping`, `issues[]` (e.g. `OUT_OF_STOCK`, `VOUCHER_INVALID`, `EXPRESS_UNAVAILABLE`) and `canCheckout`.

Delivery rules (all configurable): standard Rs. 199, express Rs. 299 within **3 hours** in express cities (Lahore),
free delivery from Rs. 10,000 subtotal. Express requires every product to be express-eligible.

## Orders (Cash on Delivery)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/orders` | user | `{ items, addressId, deliveryType, voucherCode?, customerNote? }` |
| GET | `/orders` | user | My orders (summary, paginated) |
| GET | `/orders/{id}` | user | Detail with `timeline` and `statusHistory` |
| POST | `/orders/{id}/cancel` | user | Allowed while `PLACED` or `CONFIRMED`; restocks items |

Status flow: `PLACED → CONFIRMED → PACKED → SHIPPED → DELIVERED`, plus `CANCELLED` and `RETURNED`.
Placing an order re-prices the cart, reserves stock in the same transaction and returns `400 CART_INVALID`
with the issues if anything changed.

## Custom requests & gifts

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/custom-requests` | user | Create. `requestType`: `CUSTOM_ITEM` or `GIFT` |
| GET | `/custom-requests` | user | My requests |
| GET | `/custom-requests/{id}` | user | Detail incl. `quote` |
| POST | `/custom-requests/{id}/accept-quote` | user | Creates a COD order; returns `orderId` |
| POST | `/custom-requests/{id}/cancel` | user | While still open |

Give either `addressId` (a saved address) or `deliveryAddress` (inline; for gifts this is the recipient).
Gift options: `giftMessage`, `giftWrap`, `hideSender`, `deliverOn`.
Flow: `SUBMITTED → IN_REVIEW → QUOTED → CONFIRMED` (or `UNAVAILABLE` / `CANCELLED`). Quotes expire after 2 days by default.

## Wishlist

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/wishlist` | user | Saved products |
| PUT | `/wishlist/{productId}` | user | Add (idempotent) |
| DELETE | `/wishlist/{productId}` | user | Remove (idempotent) |

## Storefront, SEO & uploads

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/storefront/config` | – | Fees, express hours/cities, payment methods. **Never hard-code these in the apps.** |
| GET | `/storefront/home` | – | Banners, stories, featured categories, new arrivals, bestsellers, on sale |
| GET | `/seo/sitemap` | – | Every public product/category path + `updatedAt` for Next.js `sitemap.xml` |
| POST | `/uploads/presigned-url` | user | `{ fileName, contentType, folder }` → `uploadUrl` (PUT the file there) + `fileUrl` |

Upload folders: `avatars`, `custom-requests`, `reviews` (any user); `products`, `content` (staff). JPEG/PNG/WebP only.

### SEO notes for the Next.js site
- Product URL: `/product/{slug}`, category URL: `/category/{slug}` (matches `seo.canonicalUrl` and the sitemap).
- Use `seo.title`, `seo.description`, `seo.image` for `<title>`, meta description and Open Graph tags.
- Build JSON-LD `Product` data from `title`, `images`, `price`, `inStock`, `ratingAvg`, `reviewCount`;
  `BreadcrumbList` from `breadcrumbs`.
- Render product and category pages on the server (SSR/ISR) and revalidate when `updatedAt` changes.

## Admin & staff (`/admin`)

Roles: `customer`, `staff` (orders, custom requests, stock), `admin` (everything).

| Area | Endpoints |
| --- | --- |
| Categories | `GET/POST /admin/categories`, `PATCH/DELETE /admin/categories/{id}` |
| Products | `GET/POST /admin/products`, `GET/PATCH/DELETE /admin/products/{id}` (DELETE archives) |
| Variants | `POST /admin/products/{id}/variants`, `PATCH/DELETE /admin/variants/{id}` (staff may PATCH stock) |
| Orders | `GET /admin/orders?status=&q=`, `GET /admin/orders/{id}`, `PATCH /admin/orders/{id}/status` |
| Custom requests | `GET /admin/custom-requests`, `GET …/{id}`, `POST …/{id}/quote` (`unitPrice`), `PATCH …/{id}/status` |
| Vouchers | `GET/POST /admin/vouchers`, `PATCH /admin/vouchers/{id}` |
| Home content | `GET/POST /admin/content`, `PATCH/DELETE /admin/content/{id}` |
| Users | `GET /admin/users?q=&role=`, `PATCH /admin/users/{id}` (role, active) |
