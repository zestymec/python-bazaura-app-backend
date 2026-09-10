"""
Bazaura.pk - Catalog, Product & Review Pydantic Schemas
Handles serialized outputs for products, categories, variants, and customer reviews
formatted with camelCase field naming for the React Native mobile client.
"""

from typing import Any, Dict, List, Optional
from pydantic import Field
from app.schemas.base import BaseSchema


class CategoryResponse(BaseSchema):
    id: str
    name: str
    slug: str
    icon_name: str
    image: str = Field(..., validation_alias="image_url")
    item_count: int
    is_popular: bool


class VariantOption(BaseSchema):
    id: str
    label: str
    value: str
    in_stock: bool
    price_modifier: int = 0


class ProductVariantSchema(BaseSchema):
    id: str
    name: str
    options: List[VariantOption]


class ProductReviewSchema(BaseSchema):
    id: str
    user_name: str
    user_avatar: Optional[str] = None
    rating: int
    date: str
    comment: str
    verified_purchase: bool
    city_name: str


class ProductResponse(BaseSchema):
    id: str
    title: str
    brand: str
    category: Optional[str] = None
    sub_category: Optional[str] = None
    price: int
    original_price: Optional[int] = None
    discount_percent: Optional[int] = None
    rating: float
    review_count: int
    description: str
    images: List[str]
    features: List[str]
    in_stock: bool
    stock_count: int
    is_lahore_express_2hour: bool
    nationwide_delivery_days: str
    badge: Optional[str] = None
    tags: List[str] = []
    specifications: Dict[str, Any] = {}
    variants: List[ProductVariantSchema] = []
    reviews: Optional[List[ProductReviewSchema]] = None


class FlashDealsData(BaseSchema):
    countdown_seconds_remaining: int
    items: List[ProductResponse]


class VoucherResponse(BaseSchema):
    code: str
    discount_type: str
    value: int
    min_order_amount: Optional[int] = None
    max_discount: Optional[int] = None
    description: str
