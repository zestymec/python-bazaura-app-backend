# Bazaura.pk — Frontend Integration Spec (React Native)

> **Audience:** the developer, or AI coding agent, building the Bazaura.pk React Native app.
> This file has everything needed to connect the app to the backend: every endpoint, the exact
> request/response types, the business rules, the screen behaviour and the order to build things in.
> Generated from backend API v1 (OpenAPI spec: `docs/openapi.json`, live at `GET /api/v1/openapi.json`).

---

## 0. Rules for whoever implements this

1. **Do not invent endpoints or fields.** Use only what is listed here. If something the UI needs is missing, leave a `// TODO(backend):` comment and say so; don't fake it.
2. **The server is the source of truth for money.** Never calculate totals, discounts or delivery fees in the app. Show what `POST /cart/quote` returns. Never send prices to the server.
3. **Never hard-code business values:** delivery fees, the express delivery window ("3 hours" today), express cities and the free-shipping threshold come from `GET /storefront/config`.
4. **Customers buy variants.** A product has size/colour variants. The cart and orders use `variantId`, never `productId`.
5. **Payment is Cash on Delivery only.** Build no payment screens, card forms or gateway SDKs.
6. **Branch on `error.code`**, never on message text. Messages are human-readable and safe to display.
7. Keep all networking in `src/api/`. Screens call hooks; hooks call the API client.
8. Build in the order of [section 10](#10-implementation-plan). Each phase must work before moving on.

---

## 1. Product context

- **Bazaura.pk** is a Pakistani clothing brand: hoodies, jackets, shirts, T-shirts, trousers, tracksuits and pants (men first; more categories later).
- Customers browse without logging in. Login (phone + SMS OTP) is required for checkout, orders, addresses, wishlist, reviews and custom requests.
- **Delivery:** Standard (nationwide, a few working days) and **Express** (same city, within N hours, currently 3, only in express cities, currently Lahore). Free delivery above a subtotal threshold.
- **Custom requests:** a customer can ask Bazaura to arrange an item that isn't in the catalog, or to **send a gift** to someone else. Staff send a price quote; when the customer accepts, an order is created.
- Currency is PKR. All amounts are whole-rupee integers. Format as `Rs. 3,499`.

---

## 2. Backend facts

| Item | Value |
| --- | --- |
| Base path | `/api/v1` |
| Base URL (local, iOS simulator) | `http://localhost:8000/api/v1` |
| Base URL (local, Android emulator) | `http://10.0.2.2:8000/api/v1` |
| Base URL (local, real phone on same Wi-Fi) | `http://<laptop-LAN-IP>:8000/api/v1` |
| Base URL (shared testing / production) | Provided by the backend owner; put it in env config |
| Format | JSON, **camelCase keys** both ways |
| Auth | `Authorization: Bearer <accessToken>` |
| Access token lifetime | 60 minutes (`expiresIn` is in seconds) |
| Refresh token lifetime | 30 days |
| Money | integer PKR |
| Dates | ISO-8601 UTC strings, e.g. `"2026-10-31T09:15:22.123456Z"`; display in local time |
| IDs | opaque strings with prefixes: `usr_`, `adr_`, `prd_`, `var_`, `cat_`, `ord_`, `crq_` |
| Human references | orders `BZ-261031-7KQ2`, custom requests `RQ-261031-4FZ8`; show these to customers, not IDs |
| Phone input | any PK format (`03001234567`, `+92 300 1234567`); the server normalises to `+923001234567` |

### Response envelope (every endpoint)

```json
{ "success": true, "message": "Order placed", "data": { } }
```
```json
{ "success": false, "message": "Incorrect code", "error": { "code": "OTP_INVALID", "details": null } }
```
Paginated endpoints return `data: { items: T[], meta: { page, limit, totalItems, totalPages } }`.
Pagination query: `?page=1&limit=20` (`limit` max 100).

---

## 3. Libraries and project structure

| Need | Use |
| --- | --- |
| Server state, caching, refetch | `@tanstack/react-query` |
| Token storage | `expo-secure-store` (Expo) or `react-native-keychain` (bare RN). **Never AsyncStorage for tokens.** |
| Cart persistence | `zustand` + `persist` middleware with AsyncStorage (cart holds no secrets) |
| Base URL | `EXPO_PUBLIC_API_URL` (Expo) or `react-native-config` (bare RN) |

```
src/api/
  types.ts        ← section 4, copy verbatim
  client.ts       ← section 5
  endpoints.ts    ← one typed function per endpoint (section 6)
  queryKeys.ts    ← section 9
  hooks/          ← useProducts, useProduct, useCartQuote, useOrders, ...
src/store/
  cart.ts         ← local cart (variantId + quantity)
  auth.ts         ← isLoggedIn + current user
```

---

## 4. TypeScript types (`src/api/types.ts`)

Copy this file verbatim. It is generated from the backend schema. Response fields are always present
(nullable ones are `| null`). In request bodies, `?` marks optional fields.

```ts
// ---- Enums ----
export type Gender = "MEN" | "WOMEN" | "UNISEX" | "KIDS";
export type Season = "SUMMER" | "WINTER" | "ALL_SEASON";
export type DeliveryType = "STANDARD" | "EXPRESS";
export type OrderStatus = "PLACED" | "CONFIRMED" | "PACKED" | "SHIPPED" | "DELIVERED" | "CANCELLED" | "RETURNED";
export type CustomRequestType = "CUSTOM_ITEM" | "GIFT";
export type CustomRequestStatus = "SUBMITTED" | "IN_REVIEW" | "QUOTED" | "CONFIRMED" | "UNAVAILABLE" | "CANCELLED";
export type ContentType = "BANNER" | "STORY";
export type ContentTargetType = "CATEGORY" | "PRODUCT" | "COLLECTION" | "CUSTOM_REQUEST" | "URL";
export type ProductSort = "newest" | "popular" | "price_asc" | "price_desc" | "rating";

// ---- Envelope ----
export interface ApiResponse<T> {
  success: boolean;
  message: string | null;
  data: T | null;
}
export interface ApiErrorBody {
  success: false;
  message: string;
  error: { code: string; details: unknown };
}
export interface Page<T> {
  items: T[];
  meta: PageMeta;
}

// ---- Request bodies (send these) ----
export interface OtpRequest {
  /** e.g. "03001234567" */
  phone: string;
}
export interface OtpVerify {
  /** e.g. "03001234567" */
  phone: string;
  /** e.g. "123456"; minLength 4; maxLength 8 */
  code: string;
  /** Used only when creating a new account */
  fullName?: string | null;
}
export interface RefreshRequest {
  refreshToken: string;
}
export interface UserUpdate {
  fullName?: string | null;
  email?: string | null;
  avatarUrl?: string | null;
  city?: string | null;
}
export interface AddressCreate {
  /** e.g. "Home" */
  label?: string | null;
  /** minLength 1; maxLength 128 */
  fullName: string;
  phone: string;
  alternatePhone?: string | null;
  /** minLength 1 */
  addressLine1: string;
  addressLine2?: string | null;
  /** e.g. "Gulberg III"; minLength 1; maxLength 128 */
  area: string;
  /** e.g. "Lahore"; minLength 1; maxLength 64 */
  city: string;
  postalCode?: string | null;
  /** default false */
  isDefault?: boolean;
}
export interface AddressUpdate {
  label?: string | null;
  fullName?: string | null;
  phone?: string | null;
  alternatePhone?: string | null;
  addressLine1?: string | null;
  addressLine2?: string | null;
  area?: string | null;
  city?: string | null;
  postalCode?: string | null;
  isDefault?: boolean | null;
}
export interface CartItemIn {
  /** The size/colour variant being bought */
  variantId: string;
  /** min 1; max 20 */
  quantity: number;
}
export interface CartQuoteRequest {
  items: CartItemIn[];
  voucherCode?: string | null;
  /** default "STANDARD" */
  deliveryType?: DeliveryType;
  /** Delivery city; needed to check express eligibility */
  city?: string | null;
}
export interface OrderCreate {
  items: CartItemIn[];
  addressId: string;
  /** default "STANDARD" */
  deliveryType?: DeliveryType;
  voucherCode?: string | null;
  customerNote?: string | null;
}
export interface OrderCancel {
  reason?: string | null;
}
export interface DeliveryAddressIn {
  /** e.g. "Home" */
  label?: string | null;
  /** minLength 1; maxLength 128 */
  fullName: string;
  phone: string;
  alternatePhone?: string | null;
  /** minLength 1 */
  addressLine1: string;
  addressLine2?: string | null;
  /** e.g. "Gulberg III"; minLength 1; maxLength 128 */
  area: string;
  /** e.g. "Lahore"; minLength 1; maxLength 64 */
  city: string;
  postalCode?: string | null;
}
export interface CustomRequestCreate {
  /** default "CUSTOM_ITEM" */
  requestType?: CustomRequestType;
  /** e.g. "Black oversized hoodie, size XL"; minLength 2; maxLength 200 */
  itemName: string;
  /** minLength 5; maxLength 2000 */
  description: string;
  /** default 1; min 1; max 50 */
  quantity?: number;
  /** Expected price in PKR */
  budget?: number | null;
  referenceUrl?: string | null;
  imageUrls?: string[];
  /** default "STANDARD" */
  deliveryType?: DeliveryType;
  addressId?: string | null;
  deliveryAddress?: DeliveryAddressIn | null;
  giftMessage?: string | null;
  /** default false */
  giftWrap?: boolean;
  /** default false */
  hideSender?: boolean;
  deliverOn?: string | null;
}
export interface CustomRequestCancel {
  reason?: string | null;
}
export interface ReviewCreate {
  /** min 1; max 5 */
  rating: number;
  title?: string | null;
  /** minLength 3; maxLength 2000 */
  comment: string;
  sizePurchased?: string | null;
}
export interface PresignedUploadRequest {
  fileName: string;
  contentType: string;
  /** default "uploads" */
  folder?: string;
}

// ---- Response data (you receive these) ----
export interface PageMeta {
  page: number;
  limit: number;
  totalItems: number;
  totalPages: number;
}
export interface OtpRequestResult {
  expiresInSeconds: number;
  resendAvailableInSeconds: number;
}
export interface TokenPair {
  accessToken: string;
  refreshToken: string;
  /** default "bearer" */
  tokenType: string;
  expiresIn: number;
}
export interface UserOut {
  id: string;
  phone: string;
  fullName: string | null;
  email: string | null;
  avatarUrl: string | null;
  city: string | null;
  role: "customer" | "staff" | "admin";
  createdAt: string;
}
export interface AuthResult {
  accessToken: string;
  refreshToken: string;
  /** default "bearer" */
  tokenType: string;
  expiresIn: number;
  user: UserOut;
  isNewUser: boolean;
}
export interface AddressOut {
  /** e.g. "Home" */
  label: string | null;
  /** minLength 1; maxLength 128 */
  fullName: string;
  phone: string;
  alternatePhone: string | null;
  /** minLength 1 */
  addressLine1: string;
  addressLine2: string | null;
  /** e.g. "Gulberg III"; minLength 1; maxLength 128 */
  area: string;
  /** e.g. "Lahore"; minLength 1; maxLength 64 */
  city: string;
  postalCode: string | null;
  id: string;
  isDefault: boolean;
  isExpressEligible: boolean;
}
export interface UserProfile {
  id: string;
  phone: string;
  fullName: string | null;
  email: string | null;
  avatarUrl: string | null;
  city: string | null;
  role: "customer" | "staff" | "admin";
  createdAt: string;
  addresses: AddressOut[];
}
export interface AddressSnapshot {
  fullName: string;
  phone: string;
  alternatePhone: string | null;
  addressLine1: string;
  addressLine2: string | null;
  area: string;
  city: string;
  postalCode: string | null;
}
export interface SeoMeta {
  title: string;
  description: string;
  canonicalUrl: string;
  image: string | null;
}
export interface CategoryRef {
  id: string;
  name: string;
  slug: string;
}
export interface CategoryOut {
  id: string;
  name: string;
  slug: string;
  parentId: string | null;
  description: string | null;
  imageUrl: string | null;
  iconName: string | null;
  isFeatured: boolean;
  displayOrder: number;
}
export interface CategoryNode {
  id: string;
  name: string;
  slug: string;
  parentId: string | null;
  description: string | null;
  imageUrl: string | null;
  iconName: string | null;
  isFeatured: boolean;
  displayOrder: number;
  children: CategoryNode[];
}
export interface CategoryDetail {
  id: string;
  name: string;
  slug: string;
  parentId: string | null;
  description: string | null;
  imageUrl: string | null;
  iconName: string | null;
  isFeatured: boolean;
  displayOrder: number;
  breadcrumbs: CategoryRef[];
  children: CategoryOut[];
  seo: SeoMeta;
}
export interface VariantOut {
  id: string;
  sku: string;
  size: string | null;
  color: string | null;
  colorHex: string | null;
  price: number;
  stockQuantity: number;
  inStock: boolean;
}
export interface ProductCard {
  id: string;
  slug: string;
  title: string;
  brand: string;
  price: number;
  compareAtPrice: number | null;
  discountPercent: number | null;
  primaryImage: string | null;
  images: string[];
  badge: string | null;
  gender: Gender | null;
  season: Season | null;
  category: CategoryRef | null;
  ratingAvg: number;
  reviewCount: number;
  inStock: boolean;
  isExpressEligible: boolean;
  availableSizes: string[];
  availableColors: string[];
}
export interface ProductDetail {
  id: string;
  slug: string;
  title: string;
  brand: string;
  price: number;
  compareAtPrice: number | null;
  discountPercent: number | null;
  primaryImage: string | null;
  images: string[];
  badge: string | null;
  gender: Gender | null;
  season: Season | null;
  category: CategoryRef | null;
  ratingAvg: number;
  reviewCount: number;
  inStock: boolean;
  isExpressEligible: boolean;
  availableSizes: string[];
  availableColors: string[];
  shortDescription: string | null;
  description: string;
  fabric: string | null;
  fit: string | null;
  careInstructions: string | null;
  sizeChartUrl: string | null;
  attributes: Record<string, unknown>;
  tags: string[];
  variants: VariantOut[];
  breadcrumbs: CategoryRef[];
  seo: SeoMeta;
  updatedAt: string;
}
export interface ReviewOut {
  id: string;
  authorName: string;
  rating: number;
  title: string | null;
  comment: string;
  sizePurchased: string | null;
  isVerifiedPurchase: boolean;
  createdAt: string;
}
export interface CartLine {
  variantId: string;
  productId: string;
  productSlug: string;
  title: string;
  imageUrl: string | null;
  sku: string;
  size: string | null;
  color: string | null;
  unitPrice: number;
  quantity: number;
  lineTotal: number;
  availableQuantity: number;
}
export interface CartIssue {
  code: "VARIANT_NOT_FOUND" | "OUT_OF_STOCK" | "INSUFFICIENT_STOCK" | "VOUCHER_INVALID" | "EXPRESS_UNAVAILABLE";
  message: string;
  variantId: string | null;
}
export interface AppliedVoucher {
  code: string;
  description: string;
  discount: number;
}
export interface DeliveryOption {
  type: DeliveryType;
  label: string;
  estimate: string;
  fee: number;
  available: boolean;
}
export interface CartQuote {
  lines: CartLine[];
  itemCount: number;
  subtotal: number;
  discount: number;
  deliveryFee: number;
  /** default 0 */
  extraFee: number;
  total: number;
  deliveryType: DeliveryType;
  deliveryEstimate: string;
  deliveryOptions: DeliveryOption[];
  freeShippingThreshold: number;
  amountToFreeShipping: number;
  appliedVoucher: AppliedVoucher | null;
  issues: CartIssue[];
  canCheckout: boolean;
}
export interface OrderItemOut {
  id: string;
  productId: string | null;
  variantId: string | null;
  title: string;
  productSlug: string | null;
  imageUrl: string | null;
  sku: string | null;
  size: string | null;
  color: string | null;
  unitPrice: number;
  quantity: number;
  lineTotal: number;
}
export interface OrderStatusEventOut {
  status: OrderStatus;
  note: string | null;
  createdAt: string;
}
export interface TimelineStep {
  status: OrderStatus;
  label: string;
  isCompleted: boolean;
  isCurrent: boolean;
  completedAt: string | null;
}
export interface OrderSummary {
  id: string;
  orderNumber: string;
  status: OrderStatus;
  source: "CATALOG" | "CUSTOM_REQUEST";
  total: number;
  itemCount: number;
  deliveryType: DeliveryType;
  createdAt: string;
}
export interface OrderOut {
  id: string;
  orderNumber: string;
  status: OrderStatus;
  source: "CATALOG" | "CUSTOM_REQUEST";
  total: number;
  itemCount: number;
  deliveryType: DeliveryType;
  createdAt: string;
  subtotal: number;
  discount: number;
  deliveryFee: number;
  extraFee: number;
  voucherCode: string | null;
  /** default "CASH_ON_DELIVERY" */
  paymentMethod: "CASH_ON_DELIVERY";
  deliveryEstimate: string;
  shippingAddress: AddressSnapshot;
  customerNote: string | null;
  cancelReason: string | null;
  canCancel: boolean;
  items: OrderItemOut[];
  timeline: TimelineStep[];
  statusHistory: OrderStatusEventOut[];
}
export interface QuoteOut {
  itemPrice: number;
  deliveryFee: number;
  extraFee: number;
  total: number;
  notes: string;
  validUntil: string;
}
export interface CustomRequestOut {
  id: string;
  requestNumber: string;
  requestType: CustomRequestType;
  status: CustomRequestStatus;
  itemName: string;
  description: string;
  quantity: number;
  budget: number | null;
  referenceUrl: string | null;
  imageUrls: string[];
  deliveryType: DeliveryType;
  deliveryAddress: AddressSnapshot;
  giftMessage: string | null;
  giftWrap: boolean;
  hideSender: boolean;
  deliverOn: string | null;
  staffNote: string | null;
  quote: QuoteOut | null;
  orderId: string | null;
  createdAt: string;
  updatedAt: string;
}
export interface ContentBlockOut {
  id: string;
  contentType: ContentType;
  title: string;
  subtitle: string | null;
  tag: string | null;
  imageUrl: string;
  mobileImageUrl: string | null;
  ctaText: string | null;
  targetType: ContentTargetType;
  targetValue: string | null;
  displayOrder: number;
}
export interface HomeFeed {
  banners: ContentBlockOut[];
  stories: ContentBlockOut[];
  featuredCategories: CategoryOut[];
  newArrivals: ProductCard[];
  bestsellers: ProductCard[];
  onSale: ProductCard[];
}
export interface StorefrontConfig {
  /** default "PKR" */
  currency: string;
  /** default ["CASH_ON_DELIVERY"] */
  paymentMethods: string[];
  freeShippingThreshold: number;
  expressDeliveryHours: number;
  expressDeliveryCities: string[];
  deliveryOptions: DeliveryOption[];
  giftWrapFee: number;
}
export interface PresignedUpload {
  uploadUrl: string;
  fileUrl: string;
  expiresInSeconds: number;
}
```

---

## 5. API client (`src/api/client.ts`)

Handles the base URL, the bearer token, envelope unwrapping, a single shared token refresh on
`TOKEN_EXPIRED`, and timeouts. A free testing server may take up to ~60 s to wake up, so the timeout is generous.

```ts
import * as SecureStore from "expo-secure-store";
import type { ApiErrorBody } from "./types";

const BASE_URL = process.env.EXPO_PUBLIC_API_URL!; // e.g. http://10.0.2.2:8000/api/v1
const TIMEOUT_MS = 70_000;

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
    public details?: unknown,
  ) {
    super(message);
  }
}

const ACCESS = "accessToken";
const REFRESH = "refreshToken";

export async function saveTokens(accessToken: string, refreshToken: string) {
  await SecureStore.setItemAsync(ACCESS, accessToken);
  await SecureStore.setItemAsync(REFRESH, refreshToken);
}
export async function clearTokens() {
  await SecureStore.deleteItemAsync(ACCESS);
  await SecureStore.deleteItemAsync(REFRESH);
}
export async function hasSession() {
  return !!(await SecureStore.getItemAsync(REFRESH));
}

/** Called when the session can't be recovered; wire this to the auth store (log out + show login). */
let onSessionExpired: () => void = () => {};
export function setSessionExpiredHandler(fn: () => void) {
  onSessionExpired = fn;
}

let refreshing: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  const refreshToken = await SecureStore.getItemAsync(REFRESH);
  if (!refreshToken) return false;
  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refreshToken }),
    });
    if (!res.ok) return false;
    const body = await res.json();
    await saveTokens(body.data.accessToken, body.data.refreshToken);
    return true;
  } catch {
    return false;
  }
}

async function request<T>(path: string, init: RequestInit = {}, retried = false): Promise<T> {
  const token = await SecureStore.getItemAsync(ACCESS);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers,
      },
    });
  } catch {
    throw new ApiError("NETWORK_ERROR", "Can't reach Bazaura right now. Check your connection.", 0);
  } finally {
    clearTimeout(timer);
  }

  const body = await res.json().catch(() => null);

  if (res.status === 401 && body?.error?.code === "TOKEN_EXPIRED" && !retried) {
    refreshing ??= refreshTokens().finally(() => (refreshing = null));
    if (await refreshing) return request<T>(path, init, true);
    await clearTokens();
    onSessionExpired();
  }

  if (!res.ok || !body || body.success === false) {
    const err = body as ApiErrorBody | null;
    throw new ApiError(err?.error?.code ?? "UNKNOWN_ERROR", err?.message ?? "Something went wrong", res.status, err?.error?.details);
  }
  return body.data as T;
}

export const http = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: "POST", body: data === undefined ? undefined : JSON.stringify(data) }),
  patch: <T>(path: string, data: unknown) => request<T>(path, { method: "PATCH", body: JSON.stringify(data) }),
  put: <T>(path: string) => request<T>(path, { method: "PUT" }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

/** Builds a query string, repeating array params (?size=M&size=L) and skipping empty values. */
export function qs(params: Record<string, string | number | boolean | string[] | null | undefined>) {
  const sp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "" || value === false) continue;
    if (Array.isArray(value)) value.forEach((v) => sp.append(key, v));
    else sp.append(key, String(value));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}
```

---

## 6. Endpoint catalog (customer app)

"Auth" = needs a bearer token. Every response is wrapped in the envelope; the "Returns" column is the type of `data`.

### Auth
| Method | Path | Auth | Body | Returns |
| --- | --- | --- | --- | --- |
| POST | `/auth/otp/request` | – | `OtpRequest` | `OtpRequestResult` |
| POST | `/auth/otp/verify` | – | `OtpVerify` | `AuthResult` |
| POST | `/auth/refresh` | – | `RefreshRequest` | `TokenPair` |

### Account
| Method | Path | Auth | Body | Returns |
| --- | --- | --- | --- | --- |
| GET | `/users/me` | ✔ | – | `UserProfile` |
| PATCH | `/users/me` | ✔ | `UserUpdate` | `UserProfile` |
| GET | `/users/me/addresses` | ✔ | – | `AddressOut[]` (default first) |
| POST | `/users/me/addresses` | ✔ | `AddressCreate` | `AddressOut` (201) |
| PATCH | `/users/me/addresses/{addressId}` | ✔ | `AddressUpdate` | `AddressOut` |
| DELETE | `/users/me/addresses/{addressId}` | ✔ | – | `null` |

### Storefront
| Method | Path | Auth | Body | Returns |
| --- | --- | --- | --- | --- |
| GET | `/storefront/config` | – | – | `StorefrontConfig` |
| GET | `/storefront/home` | – | – | `HomeFeed` |

### Catalog
| Method | Path | Auth | Body / Query | Returns |
| --- | --- | --- | --- | --- |
| GET | `/categories` | – | – | `CategoryNode[]` (tree) |
| GET | `/categories/{slug}` | – | – | `CategoryDetail` |
| GET | `/products` | – | query, see below | `Page<ProductCard>` |
| GET | `/products/{slugOrId}` | – | – | `ProductDetail` |
| GET | `/products/{slugOrId}/related` | – | `?limit=8` (1–20) | `ProductCard[]` |
| GET | `/products/{slugOrId}/reviews` | – | `?page&limit` | `Page<ReviewOut>` |
| POST | `/products/{slugOrId}/reviews` | ✔ | `ReviewCreate` | `ReviewOut` (201) |

`GET /products` query parameters (all optional):

| Param | Type | Notes |
| --- | --- | --- |
| `category` | string | category **slug**; includes all sub-categories |
| `gender` | `Gender` | also returns `UNISEX` products |
| `season` | `Season` | |
| `size` | string, repeatable | `?size=M&size=L`; matches only in-stock variants |
| `color` | string, repeatable | case-insensitive; matches only in-stock variants |
| `minPrice`, `maxPrice` | number | PKR |
| `q` | string | search text, 2–100 characters; searches title, brand, fabric, tags |
| `express` | boolean | only express-eligible products |
| `inStock` | boolean | only products with stock |
| `onSale` | boolean | only discounted products |
| `featured` | boolean | only featured products |
| `sort` | `ProductSort` | default `newest` |
| `page`, `limit` | number | default 1 / 20 |

### Cart & orders
| Method | Path | Auth | Body | Returns |
| --- | --- | --- | --- | --- |
| POST | `/cart/quote` | – | `CartQuoteRequest` | `CartQuote` |
| POST | `/orders` | ✔ | `OrderCreate` | `OrderOut` (201) |
| GET | `/orders` | ✔ | `?page&limit` | `Page<OrderSummary>` (newest first) |
| GET | `/orders/{orderId}` | ✔ | – | `OrderOut` |
| POST | `/orders/{orderId}/cancel` | ✔ | `OrderCancel` (optional) | `OrderOut` |

### Custom requests & gifts
| Method | Path | Auth | Body | Returns |
| --- | --- | --- | --- | --- |
| POST | `/custom-requests` | ✔ | `CustomRequestCreate` | `CustomRequestOut` (201) |
| GET | `/custom-requests` | ✔ | `?page&limit` | `CustomRequestOut[]` (newest first) |
| GET | `/custom-requests/{requestId}` | ✔ | – | `CustomRequestOut` |
| POST | `/custom-requests/{requestId}/accept-quote` | ✔ | – | `CustomRequestOut` (now has `orderId`) |
| POST | `/custom-requests/{requestId}/cancel` | ✔ | `CustomRequestCancel` (optional) | `CustomRequestOut` |

### Wishlist & uploads
| Method | Path | Auth | Body | Returns |
| --- | --- | --- | --- | --- |
| GET | `/wishlist` | ✔ | – | `ProductCard[]` (newest first) |
| PUT | `/wishlist/{productId}` | ✔ | – | `null` (idempotent add) |
| DELETE | `/wishlist/{productId}` | ✔ | – | `null` (idempotent remove) |
| POST | `/uploads/presigned-url` | ✔ | `PresignedUploadRequest` | `PresignedUpload` |

### `src/api/endpoints.ts`

```ts
import { http, qs } from "./client";
import type * as T from "./types";

export type ProductFilters = {
  category?: string; gender?: T.Gender; season?: T.Season; size?: string[]; color?: string[];
  minPrice?: number; maxPrice?: number; q?: string; express?: boolean; inStock?: boolean;
  onSale?: boolean; featured?: boolean; sort?: T.ProductSort; page?: number; limit?: number;
};

export const api = {
  // auth
  requestOtp: (body: T.OtpRequest) => http.post<T.OtpRequestResult>("/auth/otp/request", body),
  verifyOtp: (body: T.OtpVerify) => http.post<T.AuthResult>("/auth/otp/verify", body),

  // account
  me: () => http.get<T.UserProfile>("/users/me"),
  updateMe: (body: T.UserUpdate) => http.patch<T.UserProfile>("/users/me", body),
  addresses: () => http.get<T.AddressOut[]>("/users/me/addresses"),
  createAddress: (body: T.AddressCreate) => http.post<T.AddressOut>("/users/me/addresses", body),
  updateAddress: (id: string, body: T.AddressUpdate) => http.patch<T.AddressOut>(`/users/me/addresses/${id}`, body),
  deleteAddress: (id: string) => http.delete<null>(`/users/me/addresses/${id}`),

  // storefront
  config: () => http.get<T.StorefrontConfig>("/storefront/config"),
  home: () => http.get<T.HomeFeed>("/storefront/home"),

  // catalog
  categories: () => http.get<T.CategoryNode[]>("/categories"),
  category: (slug: string) => http.get<T.CategoryDetail>(`/categories/${slug}`),
  products: (f: ProductFilters = {}) => http.get<T.Page<T.ProductCard>>(`/products${qs(f)}`),
  product: (slug: string) => http.get<T.ProductDetail>(`/products/${slug}`),
  relatedProducts: (slug: string) => http.get<T.ProductCard[]>(`/products/${slug}/related`),
  reviews: (slug: string, page = 1) => http.get<T.Page<T.ReviewOut>>(`/products/${slug}/reviews${qs({ page })}`),
  createReview: (slug: string, body: T.ReviewCreate) => http.post<T.ReviewOut>(`/products/${slug}/reviews`, body),

  // cart & orders
  quoteCart: (body: T.CartQuoteRequest) => http.post<T.CartQuote>("/cart/quote", body),
  placeOrder: (body: T.OrderCreate) => http.post<T.OrderOut>("/orders", body),
  orders: (page = 1) => http.get<T.Page<T.OrderSummary>>(`/orders${qs({ page })}`),
  order: (id: string) => http.get<T.OrderOut>(`/orders/${id}`),
  cancelOrder: (id: string, body: T.OrderCancel = {}) => http.post<T.OrderOut>(`/orders/${id}/cancel`, body),

  // custom requests
  createCustomRequest: (body: T.CustomRequestCreate) => http.post<T.CustomRequestOut>("/custom-requests", body),
  customRequests: (page = 1) => http.get<T.CustomRequestOut[]>(`/custom-requests${qs({ page })}`),
  customRequest: (id: string) => http.get<T.CustomRequestOut>(`/custom-requests/${id}`),
  acceptQuote: (id: string) => http.post<T.CustomRequestOut>(`/custom-requests/${id}/accept-quote`),
  cancelCustomRequest: (id: string, body: T.CustomRequestCancel = {}) =>
    http.post<T.CustomRequestOut>(`/custom-requests/${id}/cancel`, body),

  // wishlist & uploads
  wishlist: () => http.get<T.ProductCard[]>("/wishlist"),
  addToWishlist: (productId: string) => http.put<null>(`/wishlist/${productId}`),
  removeFromWishlist: (productId: string) => http.delete<null>(`/wishlist/${productId}`),
  presignUpload: (body: T.PresignedUploadRequest) => http.post<T.PresignedUpload>("/uploads/presigned-url", body),
};
```

---

## 7. Feature specs

### 7.1 App start
1. Fetch `api.config()` and keep it in React Query (`staleTime` 10 min). Read every fee, delivery label and estimate, the express hours and the express city list from it.
2. Set the logged-in flag from `hasSession()`. If logged in, fetch `api.me()` in the background.
3. Register `setSessionExpiredHandler(() => { authStore.logout(); queryClient.clear(); navigate to Login })`.
4. Read config defensively: the backend may add fields later (e.g. a forced-update flag). Ignore unknown fields.

### 7.2 Login (phone → OTP)
- **Screen 1, phone:** input with a `03XX XXXXXXX` hint, then `api.requestOtp({ phone })`.
  - Start a resend countdown from `resendAvailableInSeconds` (60). The code is valid for `expiresInSeconds` (300).
  - `OTP_COOLDOWN` / `OTP_RATE_LIMITED` (429): show `message`, which says how long to wait.
  - `VALIDATION_ERROR` (422): "Enter a valid Pakistani mobile number".
- **Screen 2, code:** 6-digit input with auto-submit, then `api.verifyOtp({ phone, code })`.
  - Success: `saveTokens(accessToken, refreshToken)`, store `user`, invalidate user queries.
  - If `isNewUser` is true or `user.fullName` is null, show a "What's your name?" step, then `api.updateMe({ fullName })`.
  - `OTP_INVALID`: shake the field and say "Incorrect code". `OTP_EXPIRED`: offer "Send a new code". `OTP_LOCKED`: "Too many attempts, request a new code".
- **Login gate:** when a guest taps Checkout, Wishlist, Write review or Request an item, open Login and return to the same action afterwards.
- **Logout:** `clearTokens()`, reset the auth store, `queryClient.clear()`. Keep the local cart. There is no logout endpoint.

### 7.3 Home
`api.home()` returns everything for the home screen:
- `banners` (`ContentBlockOut[]`): carousel. Use `mobileImageUrl ?? imageUrl`; button text from `ctaText`.
- `stories`: round avatars row.
- `featuredCategories`: chips or tiles.
- `newArrivals`, `bestsellers`, `onSale`: horizontal product rails (`ProductCard`).
- Empty arrays are possible; hide empty sections.

**Banner/story tap → navigation**, based on `targetType` / `targetValue`:

| targetType | targetValue | Navigate to |
| --- | --- | --- |
| `CATEGORY` | category slug | Product list with `{ category: targetValue }` |
| `PRODUCT` | product slug | Product detail |
| `COLLECTION` | query string, e.g. `season=WINTER&onSale=true` | Product list with those filters parsed from the string |
| `CUSTOM_REQUEST` | – | Custom request form |
| `URL` | https URL | Open in the in-app browser |

### 7.4 Categories & product list
- `api.categories()` returns a tree: top-level (e.g. "Men") with `children` (Hoodies, Jackets, …). Sort by `displayOrder`.
- Product list screen = `useInfiniteQuery` over `api.products(filters)` with `page`; stop when `meta.page >= meta.totalPages`.
- Filter sheet: sizes, colours, price range, season, express only, in stock, on sale. Sort menu: Newest, Popular, Price low–high, Price high–low, Top rated (`ProductSort`).
- Search: debounce 300 ms; send `q` only when it has 2+ characters.
- **Product card:** `primaryImage`; `title`; `price` formatted; if `compareAtPrice` is set, show it struck through plus a `-{discountPercent}%` tag; `badge` (NEW / SALE / BESTSELLER) as a pill; a "Sold out" overlay when `inStock` is false; an "Express" tag when `isExpressEligible` is true and the user's city is an express city (from config).

### 7.5 Product detail
`api.product(slug)` → `ProductDetail`.
- Gallery from `images`. Title, price (as on the card), `ratingAvg` + `reviewCount`.
- **Variant picker:** colour chips from `availableColors` (use `variants[].colorHex` for swatches when present), size chips from `availableSizes`.

```ts
const findVariant = (p: ProductDetail, size: string | null, color: string | null) =>
  p.variants.find((v) => (v.size ?? null) === size && (v.color ?? null) === color);

// Disable a size chip when no in-stock variant exists for the selected colour
const sizeEnabled = (p: ProductDetail, size: string, color: string | null) =>
  p.variants.some((v) => v.size === size && (v.color ?? null) === color && v.inStock);
```
  - Pre-select the first colour. Require a size before "Add to cart" (if the product has sizes).
  - Show `variant.price` (it can differ from the product price). Show "Only N left" when `stockQuantity <= 3`. Disable "Add to cart" when `!variant.inStock`.
  - Products without size or colour have exactly one variant; add it directly.
- Sections: `shortDescription`, `description`, `fabric`, `fit`, `careInstructions`, `attributes` (key/value table). "Size guide" opens `sizeChartUrl` when present.
- `breadcrumbs` can be shown as "Men › Hoodies". `seo` is for the website; the app ignores it.
- Below: `api.relatedProducts(slug)` rail and the first page of `api.reviews(slug)`.
- Heart icon: wishlist toggle (7.10).

### 7.6 Cart
- **Local state only:** `{ variantId: string; quantity: number }[]`, persisted. Add the same variant again = increase quantity. Quantity 1–20 per line.
- **Display data comes from the server.** On cart open, on any change (debounce 400 ms), and on voucher, delivery type or city change, call:

```ts
api.quoteCart({
  items: cart.map(({ variantId, quantity }) => ({ variantId, quantity })),
  voucherCode: appliedCode || null,
  deliveryType,            // "STANDARD" | "EXPRESS"
  city: selectedAddress?.city ?? user?.city ?? null,
});
```
- Render each `lines[]` entry: `imageUrl`, `title`, `size` / `color`, `unitPrice`, `quantity` stepper, `lineTotal`.
- Summary: `subtotal`, `discount` (when > 0, with `appliedVoucher.code`), `deliveryFee` ("Free" when 0), `extraFee` (when > 0), **`total`**.
- Free-shipping bar: when `amountToFreeShipping > 0`, show "Add Rs. {amountToFreeShipping} more for free delivery" with progress `subtotal / freeShippingThreshold`.
- Delivery selector: from `deliveryOptions` (`label`, `estimate`, `fee`); disable options with `available: false`.
- **Issues** (`issues[]`). Show them inline and disable checkout while `canCheckout` is false:

| code | UI |
| --- | --- |
| `OUT_OF_STOCK` | Mark the line (match `variantId`) "Sold out" and offer Remove |
| `INSUFFICIENT_STOCK` | "Only {availableQuantity} left" with a button to set the quantity to that number |
| `VARIANT_NOT_FOUND` | Remove that `variantId` from the local cart automatically and show a toast |
| `VOUCHER_INVALID` | Show `message` under the voucher field; clear the applied code |
| `EXPRESS_UNAVAILABLE` | Switch back to STANDARD and show `message` |

### 7.7 Addresses
- List: `api.addresses()` (default first). Each `AddressOut` has `isExpressEligible`; show an "Express available" tag.
- Form fields: `label` (Home/Office), `fullName`, `phone`, `alternatePhone`, `addressLine1`, `addressLine2`, `area`, `city`, `postalCode`, `isDefault`.
- City: a picker with common cities plus free text. Express eligibility depends on it.
- The first address automatically becomes the default. Maximum 10 (`ADDRESS_LIMIT`).
- `VALIDATION_ERROR` returns `details: [{ field, message }]`; `field` is the camelCase name, so show each message under its field.

### 7.8 Checkout (Cash on Delivery)
1. Require login, then load addresses; if there are none, open the address form first.
2. Address selector (default pre-selected). Re-quote with that address's `city`.
3. Delivery option (STANDARD / EXPRESS from the quote's `deliveryOptions`), optional voucher, optional note (`customerNote`, max 500 characters).
4. Payment row: fixed text "Cash on Delivery". No other choice.
5. "Place order" (enabled only when `canCheckout`):

```ts
api.placeOrder({
  items: cart.map(({ variantId, quantity }) => ({ variantId, quantity })),
  addressId: selectedAddress.id,
  deliveryType,
  voucherCode: appliedCode || null,
  customerNote: note || null,
});
```
6. **201:** clear the local cart, invalidate the orders query, navigate to an Order Success screen showing `orderNumber`, `total`, `deliveryEstimate` and a "Track order" button.
7. **400 `CART_INVALID`:** `error.details` is a `CartIssue[]`. Go back to the cart and re-quote; the issues will show there.
8. **404 `ADDRESS_NOT_FOUND`:** refresh addresses.
9. Prevent double-submit: disable the button while the request runs.

### 7.9 Orders & tracking
- List: `useInfiniteQuery` over `api.orders(page)`. Row: `orderNumber`, date (`createdAt`), status pill, `itemCount`, `total`.
- Detail: `api.order(id)`:
  - **Timeline:** render `timeline[]` as a vertical stepper. Use `label` as the text, mark `isCompleted` steps done, highlight `isCurrent`, and show `completedAt` times. Labels come from the server.
  - Items (`items[]`: `imageUrl`, `title`, `size`, `color`, `quantity`, `lineTotal`); tapping one opens the product by `productSlug` when it is not null.
  - Price summary: `subtotal`, `discount`, `deliveryFee`, `extraFee`, `total`, plus "Cash on Delivery".
  - `shippingAddress`, `deliveryEstimate`, `customerNote`; `cancelReason` when cancelled.
  - **Cancel** button only when `canCancel`, with a confirmation sheet and an optional reason, then `api.cancelOrder(id, { reason })`. `ORDER_NOT_CANCELLABLE` (409): refetch and show `message`.
  - `source === "CUSTOM_REQUEST"` orders come from an accepted custom request; items may have no product link.
- Status pill colours: PLACED / CONFIRMED neutral, PACKED / SHIPPED in progress, DELIVERED success, CANCELLED / RETURNED muted or error.

### 7.10 Wishlist
- `api.wishlist()` returns `ProductCard[]`. Keep a `Set` of product IDs to fill the heart icons across the app.
- Toggle optimistically: `api.addToWishlist(product.id)` / `api.removeFromWishlist(product.id)`. Both are idempotent, so retrying is safe; roll back on error.
- Guests: the heart opens Login.

### 7.11 Reviews
- List on the product page (`Page<ReviewOut>`): `authorName`, `rating` stars, `title`, `comment`, `sizePurchased`, a "Verified purchase" badge when `isVerifiedPurchase`, and the date.
- Write: `rating` 1–5 (required), `comment` 3–2000 characters (required), `title` (optional, max 120), `sizePurchased` (optional). `REVIEW_EXISTS` (409): "You've already reviewed this product".
- After posting, invalidate the product and reviews queries; `ratingAvg` and `reviewCount` update on the server.

### 7.12 Custom requests & gifts
Entry points: a "Can't find it? Request it" button on empty search results and on the profile; a "Send a gift" card on home or profile.

**Form** (`CustomRequestCreate`):
- Type toggle: "Arrange for me" (`CUSTOM_ITEM`) / "Send a gift" (`GIFT`).
- `itemName` (2–200 characters, required), `description` (5–2000, required), `quantity` (1–50), `budget` (optional, PKR), `referenceUrl` (optional), photos up to 5 → `imageUrls` (see 7.14).
- Delivery: `deliveryType` STANDARD / EXPRESS (EXPRESS only when the city is in `config.expressDeliveryCities`; otherwise the server returns `EXPRESS_UNAVAILABLE`).
- Address:
  - `CUSTOM_ITEM`: choose a saved address and send `addressId`.
  - `GIFT`: a recipient form sent as `deliveryAddress` (`DeliveryAddressIn`: fullName, phone, addressLine1, area, city, …). Also allow picking a saved address.
  - Send exactly one of `addressId` or `deliveryAddress`.
- Gift extras (GIFT only): `giftMessage` (max 500), `giftWrap` toggle (show `config.giftWrapFee` when > 0), `hideSender` toggle ("Don't show my name"), `deliverOn` date (ISO string, optional).

**My requests list / detail** (`CustomRequestOut`):
- Show `requestNumber`, `itemName`, status pill and `createdAt`. Show `staffNote` when present (e.g. why it's unavailable).
- Status meanings: `SUBMITTED` "Received", `IN_REVIEW` "We're finding it", `QUOTED` "Quote ready", `CONFIRMED` "Order created", `UNAVAILABLE` "Couldn't arrange", `CANCELLED` "Cancelled".
- When `status === "QUOTED"` and `quote` exists, show a quote card: `quote.itemPrice`, `quote.deliveryFee`, `quote.extraFee`, **`quote.total`**, `quote.notes`, and "Valid until {quote.validUntil}". Buttons:
  - **Accept** → `api.acceptQuote(id)` → returns the request with `orderId`; navigate to that order's detail. `QUOTE_EXPIRED`: "This quote expired. We'll send a new one."
  - **Cancel** → `api.cancelCustomRequest(id, { reason })`.
- Cancel is allowed while the status is SUBMITTED, IN_REVIEW or QUOTED.

### 7.13 Profile
`api.me()` → `UserProfile`: `fullName`, `phone`, `email`, `avatarUrl`, `city`, `addresses`. Edit with `api.updateMe(...)`; `EMAIL_TAKEN` (409) shows under the email field. Avatar upload: see 7.14 with `folder: "avatars"`, then `updateMe({ avatarUrl: fileUrl })`.

### 7.14 Image uploads
```ts
async function uploadImage(localUri: string, folder: "avatars" | "custom-requests" | "reviews") {
  const contentType = localUri.toLowerCase().endsWith(".png") ? "image/png" : "image/jpeg";
  const { uploadUrl, fileUrl } = await api.presignUpload({ fileName: localUri.split("/").pop() ?? "photo.jpg", contentType, folder });
  const blob = await (await fetch(localUri)).blob();
  const put = await fetch(uploadUrl, { method: "PUT", headers: { "Content-Type": contentType }, body: blob });
  if (!put.ok) throw new Error("Upload failed");
  return fileUrl; // store this URL (imageUrls / avatarUrl)
}
```
- Allowed types: `image/jpeg`, `image/png`, `image/webp`. Compress or resize before upload (max ~1600 px).
- The upload URL expires after 5 minutes, so request it right before uploading.
- `STORAGE_UNAVAILABLE` means storage isn't configured yet on that server: show "Photo uploads aren't available right now" and let the form submit without photos.

---

## 8. Error handling

| HTTP | `error.code` | App behaviour |
| --- | --- | --- |
| 0 | `NETWORK_ERROR` (client-side) | Retry button; React Query retries reads automatically |
| 401 | `TOKEN_EXPIRED` | Client refreshes once and retries automatically |
| 401 | `AUTH_REQUIRED`, `TOKEN_INVALID`, `ACCOUNT_NOT_FOUND` | Log out, open Login |
| 403 | `ACCOUNT_INACTIVE` | "Your account is disabled. Please contact support." and log out |
| 404 | `PRODUCT_NOT_FOUND`, `CATEGORY_NOT_FOUND`, `ORDER_NOT_FOUND`, `ADDRESS_NOT_FOUND`, `REQUEST_NOT_FOUND`, `NOT_FOUND` | Not-found state with a Back button |
| 400 | `CART_INVALID` | Section 7.8 |
| 400 | `OTP_INVALID`, `OTP_EXPIRED`, `EXPRESS_UNAVAILABLE` | Sections 7.2 / 7.6 / 7.12 |
| 409 | `ORDER_NOT_CANCELLABLE`, `REQUEST_NOT_CANCELLABLE`, `NO_ACTIVE_QUOTE`, `QUOTE_EXPIRED`, `REVIEW_EXISTS`, `ADDRESS_LIMIT`, `EMAIL_TAKEN` | Show `message`, refetch the screen |
| 422 | `VALIDATION_ERROR` | `details: { field: string; message: string }[]`; show under form fields |
| 429 | `OTP_COOLDOWN`, `OTP_RATE_LIMITED`, `OTP_LOCKED` | Show `message` |
| 5xx / other | any | Generic "Something went wrong. Please try again." |

Do not retry mutations (orders, cancels) automatically. React Query: `retry: (count, err) => !(err instanceof ApiError) || err.status >= 500 ? count < 2 : false`.

---

## 9. Data freshness (React Query)

There are no WebSockets or push notifications yet. Data updates on refetch, so the backend can change products, prices, stock, banners and settings without an app release.

```ts
// src/api/queryKeys.ts
export const qk = {
  config: ["config"] as const,
  home: ["home"] as const,
  categories: ["categories"] as const,
  category: (slug: string) => ["category", slug] as const,
  products: (filters: object) => ["products", filters] as const,
  product: (slug: string) => ["product", slug] as const,
  related: (slug: string) => ["product", slug, "related"] as const,
  reviews: (slug: string) => ["product", slug, "reviews"] as const,
  cartQuote: (body: object) => ["cartQuote", body] as const,
  me: ["me"] as const,
  addresses: ["addresses"] as const,
  orders: ["orders"] as const,
  order: (id: string) => ["order", id] as const,
  customRequests: ["customRequests"] as const,
  customRequest: (id: string) => ["customRequest", id] as const,
  wishlist: ["wishlist"] as const,
};
```

| Query | Settings |
| --- | --- |
| config | `staleTime: 10 * 60_000` |
| home, categories | `staleTime: 2 * 60_000`, pull-to-refresh |
| products, product, related, reviews | `staleTime: 60_000`, pull-to-refresh |
| cartQuote | `staleTime: 0`, refetch on screen focus |
| order (status not DELIVERED / CANCELLED / RETURNED) | `refetchInterval: 30_000` |
| customRequest (status SUBMITTED / IN_REVIEW) | `refetchInterval: 60_000` |
| me, addresses, orders, wishlist | invalidate after related mutations |

Wire `focusManager` to React Native `AppState` so queries refetch when the app returns to the foreground.

**Invalidate after mutations:** place order → `orders`, `products` (stock changed); cancel order → `order(id)`, `orders`; accept quote → `customRequest(id)`, `customRequests`, `orders`; address changes → `addresses`, `me`; review → `product(slug)`, `reviews(slug)`; wishlist → `wishlist`.

---

## 10. Implementation plan

Each phase ends with its acceptance check working against a real backend.

| Phase | Build | Done when |
| --- | --- | --- |
| 1 | `types.ts`, `client.ts`, `endpoints.ts`, `queryKeys.ts`, QueryClient provider, env base URL, app start (7.1) | Config loads and the delivery labels show "3 hours" from the server |
| 2 | Home (7.3), categories, product list with filters, sort, search, infinite scroll (7.4) | Seed products show; `?size=XL` hides products without XL stock |
| 3 | Product detail with variant picker (7.5), local cart store, cart screen with live quote and issue handling (7.6) | Adding 2× a variant shows the server subtotal; voucher `WELCOME10` applies on a Rs. 2,000+ cart |
| 4 | Login (7.2), auth store, session-expired handling, profile (7.13), addresses (7.7) | Login works; an expired access token refreshes silently |
| 5 | Checkout (7.8), order success, orders list, order detail with timeline and cancel (7.9) | An order is placed, appears in My Orders, cancels, and stock returns |
| 6 | Wishlist (7.10), reviews (7.11) | Hearts stay in sync across screens; a review appears after posting |
| 7 | Custom requests & gifts (7.12), image uploads (7.14) | A gift request is created; after staff quote it, Accept creates an order |

---

## 11. Testing against the backend

- **Local backend:** the backend owner runs it with `make dev` (or `uvicorn app.main:app --host 0.0.0.0`). In development **every OTP is `123456`**.
- **Sample data:** `make seed` loads 7 categories (`men`, `men-hoodies`, `men-jackets`, `men-shirts`, `men-t-shirts`, `men-trousers`, `men-tracksuits`), 10 products with S–XL or waist-size variants, voucher **`WELCOME10`** (10% off, minimum Rs. 2,000, max Rs. 1,000 off) and one home banner.
- **Express testing:** use an address with city `Lahore`; any other city makes express unavailable.
- **Quotes:** custom-request quotes are sent by staff (admin APIs). Ask the backend owner to send one while you test the accept flow.
- **Interactive API docs:** `<backend>/docs` (disabled when the backend runs in production mode).

---

## 12. Out of scope (do not build yet)

- Online payments (JazzCash / EasyPaisa / cards): all orders are Cash on Delivery.
- Push notifications: planned (Expo Push). Leave a "Notifications" toggle placeholder in settings at most.
- Real-time sockets.
- Admin and staff features: these live in a separate future dashboard, not in the customer app.
- Forced update / maintenance mode: may be added to `/storefront/config` later.
