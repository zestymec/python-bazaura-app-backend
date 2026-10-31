"""
Base schema and the response envelope shared by every endpoint.

JSON uses camelCase (JavaScript convention for the React Native app and the
Next.js site) while Python code uses snake_case; the alias generator converts
between them automatically. Requests are accepted in either style.
"""

import math
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class BaseSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class ApiResponse(BaseSchema, Generic[T]):
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None


class PageMeta(BaseSchema):
    page: int
    limit: int
    total_items: int
    total_pages: int

    @classmethod
    def build(cls, page: int, limit: int, total_items: int) -> "PageMeta":
        return cls(
            page=page, limit=limit, total_items=total_items, total_pages=math.ceil(total_items / limit) if limit else 0
        )


class Page(BaseSchema, Generic[T]):
    items: List[T]
    meta: PageMeta


class PaginationParams(BaseSchema):
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit
