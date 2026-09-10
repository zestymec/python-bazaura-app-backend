"""
Bazaura.pk - Orders, Order Items & Tracking Timeline Models
Implements quick-commerce orders with frozen JSON snapshots of shipping address
and products at checkout time, along with multi-step real-time tracking timeline.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy import String, Text, Boolean, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_prefixed_id


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_prefixed_id("ord")
    )
    order_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    subtotal: Mapped[int] = mapped_column(Integer, nullable=False)
    discount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivery_fee: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    delivery_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="LAHORE_EXPRESS_2HR"
    )  # 'LAHORE_EXPRESS_2HR' or 'NATIONWIDE_STANDARD'
    estimated_delivery_text: Mapped[str] = mapped_column(String(255), nullable=False)
    shipping_address_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    payment_method: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="CASH_ON_DELIVERY"
    )  # 'CASH_ON_DELIVERY', 'JAZZCASH', 'EASYPAISA', 'DEBIT_CREDIT_CARD'
    payment_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="PENDING"
    )  # 'PENDING', 'PAID', 'COD', 'FAILED', 'REFUNDED'
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PLACED"
    )  # 'PLACED', 'CONFIRMED', 'PREPARING', 'OUT_FOR_DELIVERY_2HR', 'DELIVERED', 'CANCELLED'
    payment_reference: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="orders")  # type: ignore # noqa: F821
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan"
    )
    timeline: Mapped[List["OrderTimeline"]] = relationship(
        "OrderTimeline",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderTimeline.step_order"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_prefixed_id("item")
    )
    order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    product_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True
    )
    product_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_variants: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")


class OrderTimeline(Base):
    __tablename__ = "order_timeline"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: generate_prefixed_id("otl")
    )
    order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="timeline")
