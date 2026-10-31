"""
Public storefront data: home feed, runtime config and sitemap entries.
"""

from datetime import datetime
from typing import List, Optional

from app.schemas.cart import DeliveryOption
from app.schemas.catalog import CategoryOut, ProductCard
from app.schemas.common import BaseSchema


class ContentBlockOut(BaseSchema):
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


class HomeFeed(BaseSchema):
    banners: List[ContentBlockOut]
    stories: List[ContentBlockOut]
    featured_categories: List[CategoryOut]
    new_arrivals: List[ProductCard]
    bestsellers: List[ProductCard]
    on_sale: List[ProductCard]


class StorefrontConfig(BaseSchema):
    """
    Business settings the apps display (e.g. "Delivery in 3 hours").
    Frontends must read these instead of hard-coding them.
    """

    currency: str = "PKR"
    payment_methods: List[str] = ["CASH_ON_DELIVERY"]
    free_shipping_threshold: int
    express_delivery_hours: int
    express_delivery_cities: List[str]
    delivery_options: List[DeliveryOption]
    gift_wrap_fee: int


class SitemapEntry(BaseSchema):
    path: str
    updated_at: datetime


class Sitemap(BaseSchema):
    base_url: str
    products: List[SitemapEntry]
    categories: List[SitemapEntry]


class PresignedUploadRequest(BaseSchema):
    file_name: str
    content_type: str
    folder: str = "uploads"


class PresignedUpload(BaseSchema):
    upload_url: str
    file_url: str
    expires_in_seconds: int
