"""
Bazaura.pk - User & Address Models
Represents customer, concierge agent, rider, and admin profiles,
alongside their saved delivery addresses across Lahore and Pakistan nationwide.
"""

from typing import List, Optional
from sqlalchemy import String, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from app.core.database import Base
from app.models.base import TimestampMixin, generate_prefixed_id


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_prefixed_id("usr")
    )
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    selected_city: Mapped[str] = mapped_column(String(64), nullable=False, default="Lahore")
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="customer")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_phone_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    @hybrid_property
    def is_lahore_express_eligible(self) -> bool:
        """Dynamically identifies whether user is eligible for 2-Hour Lahore Express delivery."""
        return bool(self.selected_city and self.selected_city.strip().lower() == "lahore")

    # Relationships
    addresses: Mapped[List["ShippingAddress"]] = relationship(
        "ShippingAddress",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(ShippingAddress.is_default)"
    )
    orders: Mapped[List["Order"]] = relationship(  # type: ignore # noqa: F821
        "Order",
        back_populates="user"
    )
    custom_requests: Mapped[List["CustomItemRequest"]] = relationship(  # type: ignore # noqa: F821
        "CustomItemRequest",
        back_populates="user"
    )
    reviews: Mapped[List["ProductReview"]] = relationship(  # type: ignore # noqa: F821
        "ProductReview",
        back_populates="user"
    )
    wishlist_items: Mapped[List["WishlistItem"]] = relationship(  # type: ignore # noqa: F821
        "WishlistItem",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class ShippingAddress(Base, TimestampMixin):
    __tablename__ = "shipping_addresses"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_prefixed_id("addr")
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    alternate_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    address_line1: Mapped[str] = mapped_column(Text, nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    area: Mapped[str] = mapped_column(String(128), nullable=False)  # e.g. Gulberg III, DHA Phase 5
    city: Mapped[str] = mapped_column(String(64), nullable=False)   # e.g. Lahore, Karachi
    postal_code: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    is_lahore: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="addresses")
