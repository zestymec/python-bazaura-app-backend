"""
Discount vouchers (promo codes).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UTCDateTime, id_column, utcnow


class Voucher(Base, TimestampMixin):
    __tablename__ = "vouchers"

    id: Mapped[str] = id_column("vch")
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # stored upper-case
    description: Mapped[str] = mapped_column(Text, default="")
    discount_type: Mapped[str] = mapped_column(String(16))  # DiscountType
    value: Mapped[int] = mapped_column(Integer)  # 10 = 10% for PERCENT, Rs. 10 for FLAT
    min_order_amount: Mapped[Optional[int]] = mapped_column(Integer)
    max_discount: Mapped[Optional[int]] = mapped_column(Integer)
    usage_limit: Mapped[Optional[int]] = mapped_column(Integer)  # total uses across all customers
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    starts_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    expires_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def unavailable_reason(self) -> Optional[str]:
        now = utcnow()
        if not self.is_active:
            return "This voucher is no longer active"
        if self.starts_at and now < self.starts_at:
            return "This voucher is not active yet"
        if self.expires_at and now > self.expires_at:
            return "This voucher has expired"
        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            return "This voucher has reached its usage limit"
        return None
