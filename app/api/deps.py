"""
Reusable FastAPI dependencies: DB session, authentication and role checks.

Usage in a route:
    async def endpoint(db: DbSession, user: CurrentUser): ...
"""

from typing import Annotated, Optional

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppError, ForbiddenError, UnauthorizedError
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import PaginationParams

_bearer = HTTPBearer(auto_error=False, description="Access token from /auth/otp/verify")

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def _user_from_token(db: AsyncSession, credentials: Optional[HTTPAuthorizationCredentials]) -> User:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Authentication required", code="AUTH_REQUIRED")
    payload = decode_token(credentials.credentials, ACCESS_TOKEN_TYPE)
    user = await db.get(User, payload["sub"])
    if user is None:
        raise UnauthorizedError("Account not found", code="ACCOUNT_NOT_FOUND")
    if not user.is_active:
        raise ForbiddenError("This account has been deactivated", code="ACCOUNT_INACTIVE")
    return user


async def get_current_user(
    db: DbSession, credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)]
) -> User:
    return await _user_from_token(db, credentials)


async def get_optional_user(
    db: DbSession, credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)]
) -> Optional[User]:
    if credentials is None:
        return None
    try:
        return await _user_from_token(db, credentials)
    except AppError:
        return None


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_user)]


def require_roles(*roles: UserRole):
    async def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenError("You do not have permission to do this", code="INSUFFICIENT_ROLE")
        return user

    return checker


StaffUser = Annotated[User, Depends(require_roles(UserRole.STAFF, UserRole.ADMIN))]
AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


def get_pagination(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)) -> PaginationParams:
    return PaginationParams(page=page, limit=limit)


Pagination = Annotated[PaginationParams, Depends(get_pagination)]
