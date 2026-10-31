"""
Users, their saved addresses and one-time login codes.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.core.database import Base
from app.models.base import TimestampMixin, UTCDateTime, id_column, utcnow
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.wishlist import WishlistItem


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = id_column("usr")
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(128))
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(16), default=UserRole.CUSTOMER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)

    addresses: Mapped[List["Address"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by=lambda: (Address.is_default.desc(), Address.created_at),
    )
    orders: Mapped[List["Order"]] = relationship(back_populates="user")
    wishlist_items: Mapped[List["WishlistItem"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def is_staff(self) -> bool:
        return self.role in (UserRole.STAFF, UserRole.ADMIN)


class Address(Base, TimestampMixin):
    __tablename__ = "addresses"

    id: Mapped[str] = id_column("adr")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    label: Mapped[Optional[str]] = mapped_column(String(32))  # "Home", "Office"
    full_name: Mapped[str] = mapped_column(String(128))
    phone: Mapped[str] = mapped_column(String(20))
    alternate_phone: Mapped[Optional[str]] = mapped_column(String(20))
    address_line1: Mapped[str] = mapped_column(Text)
    address_line2: Mapped[Optional[str]] = mapped_column(Text)
    area: Mapped[str] = mapped_column(String(128))
    city: Mapped[str] = mapped_column(String(64))
    postal_code: Mapped[Optional[str]] = mapped_column(String(16))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="addresses")

    @property
    def is_express_eligible(self) -> bool:
        return settings.is_express_city(self.city)

    def snapshot(self) -> dict:
        """Frozen copy stored on orders so later edits never change past orders."""
        return {
            "full_name": self.full_name,
            "phone": self.phone,
            "alternate_phone": self.alternate_phone,
            "address_line1": self.address_line1,
            "address_line2": self.address_line2,
            "area": self.area,
            "city": self.city,
            "postal_code": self.postal_code,
        }


class OtpCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[str] = id_column("otp")
    phone: Mapped[str] = mapped_column(String(20), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
