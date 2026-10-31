"""
Admin: customer and staff accounts.
"""

from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import func, or_, select

from app.api.deps import AdminUser, DbSession, Pagination
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.admin import AdminUserOut, UserAdminUpdate
from app.schemas.common import ApiResponse, Page, PageMeta

router = APIRouter()


@router.get("/users", response_model=ApiResponse[Page[AdminUserOut]], tags=["Admin: users"])
async def list_users(
    _: AdminUser,
    db: DbSession,
    pagination: Pagination,
    q: Optional[str] = Query(None, description="Phone, name or email"),
    role: Optional[UserRole] = None,
):
    query = select(User)
    if q:
        term = f"%{q.lower()}%"
        query = query.where(
            or_(
                User.phone.like(f"%{q.lstrip('0')}%"),
                func.lower(User.full_name).like(term),
                func.lower(User.email).like(term),
            )
        )
    if role:
        query = query.where(User.role == role)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = await db.execute(query.order_by(User.created_at.desc()).offset(pagination.offset).limit(pagination.limit))
    return ApiResponse(
        data=Page(
            items=[AdminUserOut.model_validate(u) for u in rows.scalars()],
            meta=PageMeta.build(pagination.page, pagination.limit, total),
        )
    )


@router.patch("/users/{user_id}", response_model=ApiResponse[AdminUserOut], tags=["Admin: users"])
async def update_user(user_id: str, payload: UserAdminUpdate, admin: AdminUser, db: DbSession):
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    if user.id == admin.id:
        raise BadRequestError("You cannot change your own role or status", code="SELF_UPDATE_FORBIDDEN")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    await db.commit()
    return ApiResponse(message="User updated", data=AdminUserOut.model_validate(user))
