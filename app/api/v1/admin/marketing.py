"""
Admin: vouchers and home-screen content.
"""

from typing import List

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import AdminUser, DbSession, StaffUser
from app.core.exceptions import ConflictError, NotFoundError
from app.models.content import ContentBlock
from app.models.voucher import Voucher
from app.schemas.admin import (
    AdminContentBlockOut,
    ContentBlockCreate,
    ContentBlockUpdate,
    VoucherCreate,
    VoucherOut,
    VoucherUpdate,
)
from app.schemas.common import ApiResponse

router = APIRouter()


# --- Vouchers ----------------------------------------------------------------
@router.get("/vouchers", response_model=ApiResponse[List[VoucherOut]], tags=["Admin: marketing"])
async def list_vouchers(_: StaffUser, db: DbSession):
    rows = await db.execute(select(Voucher).order_by(Voucher.created_at.desc()))
    return ApiResponse(data=[VoucherOut.model_validate(v) for v in rows.scalars()])


@router.post(
    "/vouchers", response_model=ApiResponse[VoucherOut], status_code=status.HTTP_201_CREATED, tags=["Admin: marketing"]
)
async def create_voucher(payload: VoucherCreate, _: AdminUser, db: DbSession):
    voucher = Voucher(**{**payload.model_dump(), "code": payload.code.strip().upper()})
    db.add(voucher)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictError("A voucher with this code already exists", code="DUPLICATE") from None
    return ApiResponse(message="Voucher created", data=VoucherOut.model_validate(voucher))


@router.patch("/vouchers/{voucher_id}", response_model=ApiResponse[VoucherOut], tags=["Admin: marketing"])
async def update_voucher(voucher_id: str, payload: VoucherUpdate, _: AdminUser, db: DbSession):
    voucher = await db.get(Voucher, voucher_id)
    if voucher is None:
        raise NotFoundError("Voucher not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(voucher, key, value)
    await db.commit()
    return ApiResponse(message="Voucher updated", data=VoucherOut.model_validate(voucher))


# --- Content blocks ----------------------------------------------------------
@router.get("/content", response_model=ApiResponse[List[AdminContentBlockOut]], tags=["Admin: marketing"])
async def list_content(_: StaffUser, db: DbSession):
    rows = await db.execute(select(ContentBlock).order_by(ContentBlock.content_type, ContentBlock.display_order))
    return ApiResponse(data=[AdminContentBlockOut.model_validate(c) for c in rows.scalars()])


@router.post(
    "/content",
    response_model=ApiResponse[AdminContentBlockOut],
    status_code=status.HTTP_201_CREATED,
    tags=["Admin: marketing"],
)
async def create_content(payload: ContentBlockCreate, _: AdminUser, db: DbSession):
    block = ContentBlock(**payload.model_dump())
    db.add(block)
    await db.commit()
    return ApiResponse(message="Content created", data=AdminContentBlockOut.model_validate(block))


@router.patch("/content/{block_id}", response_model=ApiResponse[AdminContentBlockOut], tags=["Admin: marketing"])
async def update_content(block_id: str, payload: ContentBlockUpdate, _: AdminUser, db: DbSession):
    block = await db.get(ContentBlock, block_id)
    if block is None:
        raise NotFoundError("Content not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(block, key, value)
    await db.commit()
    return ApiResponse(message="Content updated", data=AdminContentBlockOut.model_validate(block))


@router.delete("/content/{block_id}", response_model=ApiResponse[None], tags=["Admin: marketing"])
async def delete_content(block_id: str, _: AdminUser, db: DbSession):
    block = await db.get(ContentBlock, block_id)
    if block is None:
        raise NotFoundError("Content not found")
    await db.delete(block)
    await db.commit()
    return ApiResponse(message="Content deleted")
