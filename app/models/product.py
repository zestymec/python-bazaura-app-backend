"""
Bazaura.pk - Catalog, Category, Product, Variant & Review Models
Powers the multi-category quick-commerce marketplace, product pricing in PKR,
2-Hour Lahore Express badges, dynamic variants, and verified customer reviews.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from sqlalchemy import String, Text, Boolean, Integer, Numeric, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_prefixed_id


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_prefixed_id("cat")
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    icon_name: Mapped[str] = mapped_column(String(64), nullable=False)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_popular: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    products: Mapped[List["Product"]] = relationship("Product", back_populates="category")


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_prefixed_id("prod")
    )
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    brand: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    category_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    sub_category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    price: Mapped[int] = mapped_column(Integer, nullable=False)  # Stored in PKR
    original_price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    discount_percent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rating: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, default=5.0)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    images: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    features: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    in_stock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    stock_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_lahore_express_2hour: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    nationwide_delivery_days: Mapped[str] = mapped_column(String(64), nullable=False, default="2-3 Days")
    badge: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    tags: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    specifications: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    vendor_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Relationships
    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="products")
    variants: Mapped[List["ProductVariant"]] = relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan"
    )
    reviews: Mapped[List["ProductReview"]] = relationship(
        "ProductReview",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="desc(ProductReview.created_at)"
    )


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_prefixed_id("var")
    )
    product_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. Color, Storage
    options: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="variants")


class ProductReview(Base, TimestampMixin):
    __tablename__ = "product_reviews"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_prefixed_id("rev")
    )
    product_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    user_name: Mapped[str] = mapped_column(String(128), nullable=False)
    user_avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    verified_purchase: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    city_name: Mapped[str] = mapped_column(String(64), nullable=False, default="Lahore")

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="reviews")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="reviews")  # type: ignore # noqa: F821


class Voucher(Base):
    __tablename__ = "vouchers"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_prefixed_id("vouch")
    )
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    discount_type: Mapped[str] = mapped_column(String(16), nullable=False)  # 'PERCENT' or 'FLAT'
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    min_order_amount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_discount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
