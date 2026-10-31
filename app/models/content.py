"""
Merchandising content for the home screen: hero banners and stories.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UTCDateTime, id_column, utcnow


class ContentBlock(Base, TimestampMixin):
    __tablename__ = "content_blocks"

    id: Mapped[str] = id_column("cnt")
    content_type: Mapped[str] = mapped_column(String(16), index=True)  # ContentType
    title: Mapped[str] = mapped_column(String(128))
    subtitle: Mapped[Optional[str]] = mapped_column(String(255))
    tag: Mapped[Optional[str]] = mapped_column(String(64))
    image_url: Mapped[str] = mapped_column(Text)
    mobile_image_url: Mapped[Optional[str]] = mapped_column(Text)
    cta_text: Mapped[Optional[str]] = mapped_column(String(64))
    target_type: Mapped[str] = mapped_column(String(16))  # ContentTargetType
    target_value: Mapped[Optional[str]] = mapped_column(String(255))  # slug, query string or URL
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    starts_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    ends_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)

    @property
    def is_live(self) -> bool:
        now = utcnow()
        return (
            self.is_active
            and (self.starts_at is None or self.starts_at <= now)
            and (self.ends_at is None or now <= self.ends_at)
        )
