"""
Request/response schemas for staff and admin endpoints (future dashboard).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.models.enums import (
    ContentTargetType,
    ContentType,
    CustomRequestStatus,
    DiscountType,
    Gender,
    OrderStatus,
    Season,
    UserRole,
)
from app.schemas.common import BaseSchema
from app.schemas.custom_request import CustomRequestOut
from app.schemas.order import OrderOut


# --- Categories --------------------------------------------------------------
class CategoryCreate(BaseSchema):
    name: str = Field(..., min_length=2, max_length=128)
    slug: Optional[str] = Field(None, max_length=160, description="Generated from name when omitted")
    parent_id: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    icon_name: Optional[str] = None
    display_order: int = 0
    is_featured: bool = False
    is_active: bool = True
    meta_title: Optional[str] = Field(None, max_length=70)
    meta_description: Optional[str] = Field(None, max_length=170)


class CategoryUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=2, max_length=128)
    slug: Optional[str] = Field(None, max_length=160)
    parent_id: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    icon_name: Optional[str] = None
    display_order: Optional[int] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None
    meta_title: Optional[str] = Field(None, max_length=70)
    meta_description: Optional[str] = Field(None, max_length=170)


# --- Products & variants -----------------------------------------------------
class VariantCreate(BaseSchema):
    sku: str = Field(..., min_length=2, max_length=64)
    size: Optional[str] = Field(None, max_length=16)
    color: Optional[str] = Field(None, max_length=32)
    color_hex: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    price_override: Optional[int] = Field(None, ge=0)
    stock_quantity: int = Field(0, ge=0)
    display_order: int = 0
    is_active: bool = True


class VariantUpdate(BaseSchema):
    sku: Optional[str] = Field(None, min_length=2, max_length=64)
    size: Optional[str] = Field(None, max_length=16)
    color: Optional[str] = Field(None, max_length=32)
    color_hex: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    price_override: Optional[int] = Field(None, ge=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class ProductCreate(BaseSchema):
    title: str = Field(..., min_length=2, max_length=200)
    slug: Optional[str] = Field(None, max_length=200, description="Generated from title when omitted")
    category_id: Optional[str] = None
    brand: str = "Bazaura"
    short_description: Optional[str] = Field(None, max_length=300)
    description: str = ""
    price: int = Field(..., ge=0)
    compare_at_price: Optional[int] = Field(None, ge=0)
    gender: Optional[Gender] = None
    season: Optional[Season] = None
    fabric: Optional[str] = None
    fit: Optional[str] = None
    care_instructions: Optional[str] = None
    size_chart_url: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    images: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    badge: Optional[str] = None
    is_active: bool = True
    is_featured: bool = False
    is_express_eligible: bool = True
    meta_title: Optional[str] = Field(None, max_length=70)
    meta_description: Optional[str] = Field(None, max_length=170)
    variants: List[VariantCreate] = Field(default_factory=list)


class ProductUpdate(BaseSchema):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    slug: Optional[str] = Field(None, max_length=200)
    category_id: Optional[str] = None
    brand: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = None
    price: Optional[int] = Field(None, ge=0)
    compare_at_price: Optional[int] = Field(None, ge=0)
    gender: Optional[Gender] = None
    season: Optional[Season] = None
    fabric: Optional[str] = None
    fit: Optional[str] = None
    care_instructions: Optional[str] = None
    size_chart_url: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    images: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    badge: Optional[str] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_express_eligible: Optional[bool] = None
    meta_title: Optional[str] = Field(None, max_length=70)
    meta_description: Optional[str] = Field(None, max_length=170)


# --- Vouchers ----------------------------------------------------------------
class VoucherCreate(BaseSchema):
    code: str = Field(..., min_length=3, max_length=32)
    description: str = ""
    discount_type: DiscountType
    value: int = Field(..., gt=0)
    min_order_amount: Optional[int] = Field(None, ge=0)
    max_discount: Optional[int] = Field(None, ge=0)
    usage_limit: Optional[int] = Field(None, ge=1)
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True


class VoucherUpdate(BaseSchema):
    description: Optional[str] = None
    value: Optional[int] = Field(None, gt=0)
    min_order_amount: Optional[int] = Field(None, ge=0)
    max_discount: Optional[int] = Field(None, ge=0)
    usage_limit: Optional[int] = Field(None, ge=1)
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class VoucherOut(BaseSchema):
    id: str
    code: str
    description: str
    discount_type: str
    value: int
    min_order_amount: Optional[int] = None
    max_discount: Optional[int] = None
    usage_limit: Optional[int] = None
    used_count: int
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool


# --- Content -----------------------------------------------------------------
class ContentBlockCreate(BaseSchema):
    content_type: ContentType
    title: str = Field(..., max_length=128)
    subtitle: Optional[str] = Field(None, max_length=255)
    tag: Optional[str] = Field(None, max_length=64)
    image_url: str
    mobile_image_url: Optional[str] = None
    cta_text: Optional[str] = Field(None, max_length=64)
    target_type: ContentTargetType
    target_value: Optional[str] = Field(None, max_length=255)
    display_order: int = 0
    is_active: bool = True
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class ContentBlockUpdate(BaseSchema):
    title: Optional[str] = Field(None, max_length=128)
    subtitle: Optional[str] = Field(None, max_length=255)
    tag: Optional[str] = Field(None, max_length=64)
    image_url: Optional[str] = None
    mobile_image_url: Optional[str] = None
    cta_text: Optional[str] = Field(None, max_length=64)
    target_type: Optional[ContentTargetType] = None
    target_value: Optional[str] = Field(None, max_length=255)
    display_order: Optional[int] = None
    is_active: Optional[bool] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


# --- Orders ------------------------------------------------------------------
class OrderStatusUpdate(BaseSchema):
    status: OrderStatus
    note: Optional[str] = Field(None, max_length=500)


class AdminOrderOut(OrderOut):
    user_id: str
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None


# --- Custom requests ---------------------------------------------------------
class QuoteCreate(BaseSchema):
    unit_price: int = Field(..., gt=0, description="Price of one item (PKR); multiplied by the requested quantity")
    delivery_fee: Optional[int] = Field(None, ge=0, description="Defaults to the standard/express fee")
    extra_fee: Optional[int] = Field(None, ge=0, description="Defaults to the gift wrap fee when requested")
    notes: str = ""
    valid_days: Optional[int] = Field(None, ge=1, le=30)


class CustomRequestStatusUpdate(BaseSchema):
    status: CustomRequestStatus = Field(..., description="Use IN_REVIEW or UNAVAILABLE; quoting has its own endpoint")
    staff_note: Optional[str] = Field(None, max_length=1000)


# --- Admin read models ---------------------------------------------------------
class AdminVariantOut(BaseSchema):
    id: str
    sku: str
    size: Optional[str] = None
    color: Optional[str] = None
    color_hex: Optional[str] = None
    price_override: Optional[int] = None
    price: int
    stock_quantity: int
    display_order: int
    is_active: bool


class AdminProductOut(BaseSchema):
    id: str
    slug: str
    title: str
    category_id: Optional[str] = None
    brand: str
    short_description: Optional[str] = None
    description: str
    price: int
    compare_at_price: Optional[int] = None
    gender: Optional[str] = None
    season: Optional[str] = None
    fabric: Optional[str] = None
    fit: Optional[str] = None
    care_instructions: Optional[str] = None
    size_chart_url: Optional[str] = None
    attributes: Dict[str, Any]
    images: List[str]
    tags: List[str]
    badge: Optional[str] = None
    is_active: bool
    is_featured: bool
    is_express_eligible: bool
    in_stock: bool
    sold_count: int
    rating_avg: float
    review_count: int
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    variants: List[AdminVariantOut]
    created_at: datetime
    updated_at: datetime


class AdminCategoryOut(BaseSchema):
    id: str
    parent_id: Optional[str] = None
    name: str
    slug: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    icon_name: Optional[str] = None
    display_order: int
    is_featured: bool
    is_active: bool
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None


class AdminContentBlockOut(BaseSchema):
    id: str
    content_type: str
    title: str
    subtitle: Optional[str] = None
    tag: Optional[str] = None
    image_url: str
    mobile_image_url: Optional[str] = None
    cta_text: Optional[str] = None
    target_type: str
    target_value: Optional[str] = None
    display_order: int
    is_active: bool
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class AdminUserOut(BaseSchema):
    id: str
    phone: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    role: str
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime


class UserAdminUpdate(BaseSchema):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class AdminCustomRequestOut(CustomRequestOut):
    user_id: str
