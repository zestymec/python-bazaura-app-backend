"""
Bazaura.pk - Database Base Models & Mixins
Contains ID generators and common audit timestamp columns for SQLAlchemy 2.0 models.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


def generate_prefixed_id(prefix: str) -> str:
    """Generates unique prefixed string identifier e.g. usr_..., prod_..., ord_..."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class TimestampMixin:
    """Provides automatic created_at and updated_at datetime tracking."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
