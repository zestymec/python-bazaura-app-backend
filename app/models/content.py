"""
Bazaura.pk - Editorial Content & Wishlist Database Models
Powers the mobile app's curated home screen experience (stories, hero banners)
and individual customer wishlist collections.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Text, Boolean, Integer, ForeignKey, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import generate_prefixed_id


class EditorialContent(Base):
    __tablename__ = "editorial_content"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_prefixed_id("edt")
    )
    content_type: Mapped[str] = mapped_column(String(16), nullable=False)  # 'BANNER' or 'STORY'
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    subtitle: Mapped[str] = mapped_column(String(255), nullable=True)
    tag: Mapped[str] = mapped_column(String(64), nullable=True)  # e.g. '2-HOUR DISPATCH'
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    cta_text: Mapped[str] = mapped_column(String(64), nullable=True)
    target_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="CATEGORY"
    )  # 'CATEGORY', 'PRODUCT', 'REQUEST', 'LAHORE_EXPRESS', 'EXTERNAL_URL'
    target_value: Mapped[str] = mapped_column(String(255), nullable=True)
    has_unseen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class WishlistItem(Base):
    __tablename__ = "wishlist_items"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_user_product_wishlist"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_prefixed_id("wsh")
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    product_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="wishlist_items")  # type: ignore # noqa: F821
    product: Mapped["Product"] = relationship("Product")  # type: ignore # noqa: F821
