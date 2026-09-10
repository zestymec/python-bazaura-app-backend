"""
Bazaura.pk - Bazaura Sourcing Concierge Models
Powers the unique "Request Item" concierge pipeline for unlisted/rare products.
Tracks the lifecycle: SUBMITTED -> SOURCING_IN_PROGRESS -> PRICE_QUOTED -> CONFIRMED -> DELIVERED.
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_prefixed_id


class CustomItemRequest(Base, TimestampMixin):
    __tablename__ = "custom_item_requests"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_prefixed_id("req")
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    brand_or_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    expected_price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # PKR
    reference_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    image_uris: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    urgency: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="LAHORE_2HR_EXPRESS"
    )  # 'LAHORE_2HR_EXPRESS' or 'STANDARD_NATIONWIDE'
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    delivery_address: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(String(64), nullable=False, default="Lahore")
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="SUBMITTED"
    )  # 'SUBMITTED', 'SOURCING_IN_PROGRESS', 'PRICE_QUOTED', 'CONFIRMED', 'OUT_FOR_DELIVERY', 'DELIVERED', 'UNAVAILABLE', 'CANCELLED'

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="custom_requests")  # type: ignore # noqa: F821
    quote: Mapped[Optional["SourcingQuote"]] = relationship(
        "SourcingQuote",
        back_populates="request",
        uselist=False,
        cascade="all, delete-orphan"
    )


class SourcingQuote(Base):
    __tablename__ = "sourcing_quotes"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_prefixed_id("quo")
    )
    request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("custom_item_requests.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    quoted_price: Mapped[int] = mapped_column(Integer, nullable=False)  # PKR
    estimated_delivery_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    delivery_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="LAHORE_EXPRESS_2HR"
    )  # 'LAHORE_EXPRESS_2HR' or 'NATIONWIDE_STANDARD'
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    request: Mapped["CustomItemRequest"] = relationship("CustomItemRequest", back_populates="quote")
