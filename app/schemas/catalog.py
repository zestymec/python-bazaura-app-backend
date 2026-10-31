from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.core.config import settings
from app.models.catalog import Category, Product
from app.schemas.common import BaseSchema


class SeoMeta(BaseSchema):
    """Everything the Next.js site needs for <head> tags and JSON-LD."""

    title: str
    description: str
    canonical_url: str
    image: Optional[str] = None


class CategoryRef(BaseSchema):
    id: str
    name: str
    slug: str


class CategoryOut(CategoryRef):
    parent_id: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    icon_name: Optional[str] = None
    is_featured: bool
    display_order: int


class CategoryNode(CategoryOut):
    children: List["CategoryNode"] = []


class CategoryDetail(CategoryOut):
    breadcrumbs: List[CategoryRef]
    children: List[CategoryOut]
    seo: SeoMeta

    @classmethod
    def from_category(cls, category: Category, ancestors: List[Category], children: List[Category]) -> "CategoryDetail":
        return cls(
            **CategoryOut.model_validate(category).model_dump(),
            breadcrumbs=[CategoryRef.model_validate(c) for c in [*ancestors, category]],
            children=[CategoryOut.model_validate(c) for c in children],
            seo=SeoMeta(
                title=category.meta_title or f"{category.name} | Bazaura.pk",
                description=category.meta_description
                or (
                    category.description
                    or f"Shop {category.name} online at Bazaura.pk with cash on delivery across Pakistan."
                )[:170],
                canonical_url=f"{settings.SITE_URL}/category/{category.slug}",
                image=category.image_url,
            ),
        )


class VariantOut(BaseSchema):
    id: str
    sku: str
    size: Optional[str] = None
    color: Optional[str] = None
    color_hex: Optional[str] = None
    price: int
    stock_quantity: int
    in_stock: bool


class ProductCard(BaseSchema):
    """Compact product used in listings, carousels and the wishlist."""

    id: str
    slug: str
    title: str
    brand: str
    price: int
    compare_at_price: Optional[int] = None
    discount_percent: Optional[int] = None
    primary_image: Optional[str] = None
    images: List[str]
    badge: Optional[str] = None
    gender: Optional[str] = None
    season: Optional[str] = None
    category: Optional[CategoryRef] = None
    rating_avg: float
    review_count: int
    in_stock: bool
    is_express_eligible: bool
    available_sizes: List[str]
    available_colors: List[str]


class ProductDetail(ProductCard):
    short_description: Optional[str] = None
    description: str
    fabric: Optional[str] = None
    fit: Optional[str] = None
    care_instructions: Optional[str] = None
    size_chart_url: Optional[str] = None
    attributes: Dict[str, Any]
    tags: List[str]
    variants: List[VariantOut]
    breadcrumbs: List[CategoryRef]
    seo: SeoMeta
    updated_at: datetime

    @classmethod
    def from_product(cls, product: Product, category_path: List[Category]) -> "ProductDetail":
        base = ProductCard.model_validate(product).model_dump()
        return cls(
            **base,
            short_description=product.short_description,
            description=product.description,
            fabric=product.fabric,
            fit=product.fit,
            care_instructions=product.care_instructions,
            size_chart_url=product.size_chart_url,
            attributes=product.attributes or {},
            tags=product.tags or [],
            variants=[VariantOut.model_validate(v) for v in product.active_variants],
            breadcrumbs=[CategoryRef.model_validate(c) for c in category_path],
            seo=SeoMeta(
                title=product.meta_title or f"{product.title} | Bazaura.pk",
                description=product.meta_description
                or (product.short_description or product.description or product.title)[:170],
                canonical_url=f"{settings.SITE_URL}/product/{product.slug}",
                image=product.primary_image,
            ),
            updated_at=product.updated_at,
        )


class ReviewCreate(BaseSchema):
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=120)
    comment: str = Field(..., min_length=3, max_length=2000)
    size_purchased: Optional[str] = Field(None, max_length=16)


class ReviewOut(BaseSchema):
    id: str
    author_name: str
    rating: int
    title: Optional[str] = None
    comment: str
    size_purchased: Optional[str] = None
    is_verified_purchase: bool
    created_at: datetime
