from typing import List

from fastapi import APIRouter, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import ConflictError, NotFoundError
from app.models.user import Address, User
from app.schemas.common import ApiResponse
from app.schemas.user import AddressCreate, AddressOut, AddressUpdate, UserOut, UserProfile, UserUpdate

router = APIRouter(prefix="/users/me", tags=["Account"])

MAX_ADDRESSES = 10


async def _addresses(db: AsyncSession, user: User) -> List[Address]:
    rows = await db.execute(
        select(Address).where(Address.user_id == user.id).order_by(Address.is_default.desc(), Address.created_at)
    )
    return list(rows.scalars().all())


async def _profile(db: AsyncSession, user: User) -> UserProfile:
    addresses = await _addresses(db, user)
    return UserProfile(
        **UserOut.model_validate(user).model_dump(),
        addresses=[AddressOut.model_validate(a) for a in addresses],
    )


async def _get_own_address(db: AsyncSession, user: User, address_id: str) -> Address:
    address = await db.get(Address, address_id)
    if address is None or address.user_id != user.id:
        raise NotFoundError("Address not found", code="ADDRESS_NOT_FOUND")
    return address


async def _clear_default(db: AsyncSession, user: User) -> None:
    await db.execute(update(Address).where(Address.user_id == user.id).values(is_default=False))


@router.get("", response_model=ApiResponse[UserProfile], summary="Current user's profile and addresses")
async def get_me(user: CurrentUser, db: DbSession):
    return ApiResponse(data=await _profile(db, user))


@router.patch("", response_model=ApiResponse[UserProfile], summary="Update profile")
async def update_me(payload: UserUpdate, user: CurrentUser, db: DbSession):
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictError("This email is already used by another account", code="EMAIL_TAKEN") from None
    return ApiResponse(message="Profile updated", data=await _profile(db, user))


@router.get("/addresses", response_model=ApiResponse[List[AddressOut]], summary="List saved addresses")
async def list_addresses(user: CurrentUser, db: DbSession):
    return ApiResponse(data=[AddressOut.model_validate(a) for a in await _addresses(db, user)])


@router.post(
    "/addresses", response_model=ApiResponse[AddressOut], status_code=status.HTTP_201_CREATED, summary="Add an address"
)
async def create_address(payload: AddressCreate, user: CurrentUser, db: DbSession):
    existing = await _addresses(db, user)
    if len(existing) >= MAX_ADDRESSES:
        raise ConflictError(f"You can save up to {MAX_ADDRESSES} addresses", code="ADDRESS_LIMIT")

    make_default = payload.is_default or not existing
    if make_default:
        await _clear_default(db, user)
    address = Address(user_id=user.id, **payload.model_dump(exclude={"is_default"}), is_default=make_default)
    db.add(address)
    if not user.city:
        user.city = address.city
    await db.commit()
    return ApiResponse(message="Address saved", data=AddressOut.model_validate(address))


@router.patch("/addresses/{address_id}", response_model=ApiResponse[AddressOut], summary="Update an address")
async def update_address(address_id: str, payload: AddressUpdate, user: CurrentUser, db: DbSession):
    address = await _get_own_address(db, user, address_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.pop("is_default", None):
        await _clear_default(db, user)
        address.is_default = True
    for key, value in changes.items():
        setattr(address, key, value)
    await db.commit()
    return ApiResponse(message="Address updated", data=AddressOut.model_validate(address))


@router.delete("/addresses/{address_id}", response_model=ApiResponse[None], summary="Delete an address")
async def delete_address(address_id: str, user: CurrentUser, db: DbSession):
    address = await _get_own_address(db, user, address_id)
    was_default = address.is_default
    await db.delete(address)
    await db.flush()
    if was_default:
        remaining = await _addresses(db, user)
        if remaining:
            remaining[0].is_default = True
    await db.commit()
    return ApiResponse(message="Address deleted")
