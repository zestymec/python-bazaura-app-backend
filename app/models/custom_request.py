"""
Custom requests: a customer asks Bazaura to arrange any item for them, or to
send a gift to someone else. Staff review it and send a price quote; once the
customer accepts, a normal (COD) order is created from it.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UTCDateTime, id_column
from app.models.enums import CustomRequestStatus

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User


class CustomRequest(Base, TimestampMixin):
    __tablename__ = "custom_requests"

    id: Mapped[str] = id_column("crq")
    request_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # RQ-261031-4FZ8
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    request_type: Mapped[str] = mapped_column(String(16))  # CustomRequestType
    status: Mapped[str] = mapped_column(String(16), default=CustomRequestStatus.SUBMITTED, index=True)

    item_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    budget: Mapped[Optional[int]] = mapped_column(Integer)  # customer's expected price (PKR)
    reference_url: Mapped[Optional[str]] = mapped_column(Text)
    image_urls: Mapped[List[str]] = mapped_column(JSON, default=list)

    delivery_type: Mapped[str] = mapped_column(String(16))
    # For GIFT requests this is the recipient's address, otherwise the customer's.
    delivery_address: Mapped[Dict[str, Any]] = mapped_column(JSON)

    # Gift options (ignored for CUSTOM_ITEM)
    gift_message: Mapped[Optional[str]] = mapped_column(Text)
    gift_wrap: Mapped[bool] = mapped_column(Boolean, default=False)
    hide_sender: Mapped[bool] = mapped_column(Boolean, default=False)
    deliver_on: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)

    staff_note: Mapped[Optional[str]] = mapped_column(Text)  # visible to the customer (e.g. why unavailable)
    order_id: Mapped[Optional[str]] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))

    user: Mapped["User"] = relationship()
    quote: Mapped[Optional["CustomRequestQuote"]] = relationship(
        back_populates="request", uselist=False, cascade="all, delete-orphan"
    )
    order: Mapped[Optional["Order"]] = relationship()


class CustomRequestQuote(Base, TimestampMixin):
    __tablename__ = "custom_request_quotes"

    id: Mapped[str] = id_column("quo")
    request_id: Mapped[str] = mapped_column(ForeignKey("custom_requests.id", ondelete="CASCADE"), unique=True)
    item_price: Mapped[int] = mapped_column(Integer)  # total for the requested quantity
    delivery_fee: Mapped[int] = mapped_column(Integer, default=0)
    extra_fee: Mapped[int] = mapped_column(Integer, default=0)  # gift wrap etc.
    notes: Mapped[str] = mapped_column(Text, default="")
    valid_until: Mapped[datetime] = mapped_column(UTCDateTime)
    created_by_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    request: Mapped["CustomRequest"] = relationship(back_populates="quote")

    @property
    def total(self) -> int:
        return self.item_price + self.delivery_fee + self.extra_fee
