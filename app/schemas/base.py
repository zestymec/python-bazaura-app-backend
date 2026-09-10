"""
Bazaura.pk - Base Pydantic v2 Schemas
Provides shared configuration for camelCase serialization (matching React Native client)
and standard JSON API response envelopes.
"""

from typing import Generic, Optional, TypeVar, List
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class BaseSchema(BaseModel):
    """
    Base schema enabling automatic camelCase conversion for JSON output
    while allowing snake_case fields in Python code.
    Supports ORM attribute loading via from_attributes=True.
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )


class PaginationMeta(BaseSchema):
    page: int
    limit: int
    total_items: int
    total_pages: int


class PaginatedData(BaseSchema, Generic[T]):
    items: List[T]
    pagination: PaginationMeta


class ApiResponse(BaseSchema, Generic[T]):
    """Standard Bazaura.pk API response envelope."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
