"""
Orders, their line items and status history.

All orders are Cash on Delivery for now, so no payment fields are stored.
Line items copy product details at purchase time so later catalog edits never
change what the customer actually bought.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UTCDateTime, id_column, utcnow
from app.models.enums import OrderSource, OrderStatus

if TYPE_CHECKING:
    from app.models.user import User


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[str] = id_column("ord")
    order_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # BZ-261031-7KQ2
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    source: Mapped[str] = mapped_column(String(16), default=OrderSource.CATALOG)
    status: Mapped[str] = mapped_column(String(16), default=OrderStatus.PLACED, index=True)

    subtotal: Mapped[int] = mapped_column(Integer)
    discount: Mapped[int] = mapped_column(Integer, default=0)
    delivery_fee: Mapped[int] = mapped_column(Integer, default=0)
    extra_fee: Mapped[int] = mapped_column(Integer, default=0)  # e.g. gift wrapping
    total: Mapped[int] = mapped_column(Integer)
    voucher_code: Mapped[Optional[str]] = mapped_column(String(32))

    delivery_type: Mapped[str] = mapped_column(String(16))
    delivery_estimate: Mapped[str] = mapped_column(String(128))
    shipping_address: Mapped[Dict[str, Any]] = mapped_column(JSON)
    customer_note: Mapped[Optional[str]] = mapped_column(Text)
    cancel_reason: Mapped[Optional[str]] = mapped_column(Text)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)

    user: Mapped["User"] = relationship(back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    status_history: Mapped[List["OrderStatusEvent"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusEvent.created_at",
    )

    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="quantity_positive"),)

    id: Mapped[str] = id_column("oit")
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[Optional[str]] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    variant_id: Mapped[Optional[str]] = mapped_column(ForeignKey("product_variants.id", ondelete="SET NULL"))

    # Snapshot of what was bought
    title: Mapped[str] = mapped_column(String(200))
    product_slug: Mapped[Optional[str]] = mapped_column(String(200))
    image_url: Mapped[Optional[str]] = mapped_column(Text)
    sku: Mapped[Optional[str]] = mapped_column(String(64))
    size: Mapped[Optional[str]] = mapped_column(String(16))
    color: Mapped[Optional[str]] = mapped_column(String(32))
    unit_price: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer)

    order: Mapped["Order"] = relationship(back_populates="items")

    @property
    def line_total(self) -> int:
        return self.unit_price * self.quantity


class OrderStatusEvent(Base):
    __tablename__ = "order_status_events"

    id: Mapped[str] = id_column("ose")
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16))
    note: Mapped[Optional[str]] = mapped_column(Text)
    created_by_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    order: Mapped["Order"] = relationship(back_populates="status_history")
