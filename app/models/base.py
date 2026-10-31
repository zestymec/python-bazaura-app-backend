"""
Shared column types, ID generation and timestamp mixin for all models.
"""

import secrets
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import DateTime, String, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


def generate_id(prefix: str) -> str:
    """Readable, globally unique IDs such as `prd_9f2c4a1b7e3d4c55`."""
    return f"{prefix}_{secrets.token_hex(8)}"


class UTCDateTime(TypeDecorator):
    """
    Timezone-aware datetime that always comes back as UTC, on every database
    (SQLite drops tzinfo, which would otherwise break comparisons in tests).
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: Optional[datetime], dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value

    def process_result_value(self, value: Optional[datetime], dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value


def id_column(prefix: str) -> Mapped[str]:
    return mapped_column(String(32), primary_key=True, default=lambda: generate_id(prefix))


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow, nullable=False)
