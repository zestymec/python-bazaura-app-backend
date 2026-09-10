"""
Bazaura.pk - Editorial Content & Home Screen Schemas
Presents bundled payload for the React Native mobile home screen in a single request,
along with wishlist collections.
"""

from typing import List, Optional
from app.schemas.base import BaseSchema
from app.schemas.product import CategoryResponse, ProductResponse


class StoryResponse(BaseSchema):
    id: str
    title: str
    image_url: str
    has_unseen: bool
    action_type: str


class HeroBannerResponse(BaseSchema):
    id: str
    title: str
    subtitle: Optional[str] = None
    tag: Optional[str] = None
    image_url: str
    cta_text: Optional[str] = None
    target_type: str
    target_value: Optional[str] = None


class HomeScreenData(BaseSchema):
    stories: List[StoryResponse]
    hero_banners: List[HeroBannerResponse]
    categories: List[CategoryResponse]
    flash_deals: List[ProductResponse]
    express_rail: List[ProductResponse]


class WishlistResponse(BaseSchema):
    product_ids: List[str]
    products: List[ProductResponse]


class WishlistToggleRequest(BaseSchema):
    product_id: str


class WishlistToggleResponse(BaseSchema):
    product_id: str
    is_in_wishlist: bool
