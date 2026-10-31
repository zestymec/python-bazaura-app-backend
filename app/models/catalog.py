"""
Catalog: categories (nested), products, sellable variants (size/color SKUs) and reviews.

Stock lives on `ProductVariant`, because for clothing every size/colour
combination has its own inventory. A product with no size (e.g. a perfume
bottle later) simply has one variant.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, CheckConstraint, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, id_column

if TYPE_CHECKING:
    from app.models.user import User


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[str] = id_column("cat")
    parent_id: Mapped[Optional[str]] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    image_url: Mapped[Optional[str]] = mapped_column(Text)
    icon_name: Mapped[Optional[str]] = mapped_column(String(64))
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    meta_title: Mapped[Optional[str]] = mapped_column(String(70))
    meta_description: Mapped[Optional[str]] = mapped_column(String(170))

    parent: Mapped[Optional["Category"]] = relationship(remote_side="Category.id", back_populates="children")
    children: Mapped[List["Category"]] = relationship(back_populates="parent", order_by="Category.display_order")
    products: Mapped[List["Product"]] = relationship(back_populates="category")


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (CheckConstraint("price >= 0", name="price_non_negative"),)

    id: Mapped[str] = id_column("prd")
    category_id: Mapped[Optional[str]] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    brand: Mapped[str] = mapped_column(String(64), default="Bazaura")
    short_description: Mapped[Optional[str]] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")

    # Prices in whole PKR. `compare_at_price` is the struck-through "was" price.
    price: Mapped[int] = mapped_column(Integer)
    compare_at_price: Mapped[Optional[int]] = mapped_column(Integer)

    # Apparel attributes. Nullable so non-clothing categories can be added later.
    gender: Mapped[Optional[str]] = mapped_column(String(16), index=True)
    season: Mapped[Optional[str]] = mapped_column(String(16), index=True)
    fabric: Mapped[Optional[str]] = mapped_column(String(64))
    fit: Mapped[Optional[str]] = mapped_column(String(32))  # Regular, Slim, Oversized
    care_instructions: Mapped[Optional[str]] = mapped_column(Text)
    size_chart_url: Mapped[Optional[str]] = mapped_column(Text)
    # Free-form extra specs, e.g. {"GSM": "320", "Neck": "Hooded"} or {"Volume": "100ml"}
    attributes: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    images: Mapped[List[str]] = mapped_column(JSON, default=list)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    badge: Mapped[Optional[str]] = mapped_column(String(32))  # NEW, BESTSELLER, SALE

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_express_eligible: Mapped[bool] = mapped_column(Boolean, default=True)

    rating_avg: Mapped[float] = mapped_column(Numeric(3, 2), default=0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    sold_count: Mapped[int] = mapped_column(Integer, default=0)

    meta_title: Mapped[Optional[str]] = mapped_column(String(70))
    meta_description: Mapped[Optional[str]] = mapped_column(String(170))

    category: Mapped[Optional["Category"]] = relationship(back_populates="products")
    variants: Mapped[List["ProductVariant"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductVariant.display_order",
    )
    reviews: Mapped[List["ProductReview"]] = relationship(back_populates="product", cascade="all, delete-orphan")

    # The properties below need `variants` to be eager-loaded (selectinload).
    @property
    def active_variants(self) -> List["ProductVariant"]:
        return [v for v in self.variants if v.is_active]

    @property
    def in_stock(self) -> bool:
        return any(v.stock_quantity > 0 for v in self.active_variants)

    @property
    def available_sizes(self) -> List[str]:
        return _unique([v.size for v in self.active_variants if v.size])

    @property
    def available_colors(self) -> List[str]:
        return _unique([v.color for v in self.active_variants if v.color])

    @property
    def discount_percent(self) -> Optional[int]:
        if self.compare_at_price and self.compare_at_price > self.price:
            return round((self.compare_at_price - self.price) * 100 / self.compare_at_price)
        return None

    @property
    def primary_image(self) -> Optional[str]:
        return self.images[0] if self.images else None


class ProductVariant(Base, TimestampMixin):
    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("product_id", "size", "color", name="uq_product_variants_option"),
        CheckConstraint("stock_quantity >= 0", name="stock_non_negative"),
    )

    id: Mapped[str] = id_column("var")
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True)
    size: Mapped[Optional[str]] = mapped_column(String(16))  # S, M, L, XL, 32, 34 ... or 100ml
    color: Mapped[Optional[str]] = mapped_column(String(32))
    color_hex: Mapped[Optional[str]] = mapped_column(String(7))
    price_override: Mapped[Optional[int]] = mapped_column(Integer)  # null = product price
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    product: Mapped["Product"] = relationship(back_populates="variants")

    @property
    def price(self) -> int:
        return self.price_override if self.price_override is not None else self.product.price

    @property
    def in_stock(self) -> bool:
        return self.is_active and self.stock_quantity > 0


class ProductReview(Base, TimestampMixin):
    __tablename__ = "product_reviews"
    __table_args__ = (
        UniqueConstraint("product_id", "user_id", name="uq_product_reviews_product_user"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),
    )

    id: Mapped[str] = id_column("rev")
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    author_name: Mapped[str] = mapped_column(String(128))
    rating: Mapped[int] = mapped_column(Integer)
    title: Mapped[Optional[str]] = mapped_column(String(120))
    comment: Mapped[str] = mapped_column(Text)
    size_purchased: Mapped[Optional[str]] = mapped_column(String(16))
    is_verified_purchase: Mapped[bool] = mapped_column(Boolean, default=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)

    product: Mapped["Product"] = relationship(back_populates="reviews")
    user: Mapped[Optional["User"]] = relationship()


def _unique(values: List[str]) -> List[str]:
    return list(dict.fromkeys(values))
