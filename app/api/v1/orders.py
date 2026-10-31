from typing import Optional

from fastapi import APIRouter, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, Pagination
from app.models.order import Order
from app.schemas.common import ApiResponse, Page, PageMeta
from app.schemas.order import OrderCancel, OrderCreate, OrderOut, OrderSummary
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "",
    response_model=ApiResponse[OrderOut],
    status_code=status.HTTP_201_CREATED,
    summary="Place an order (Cash on Delivery)",
)
async def place_order(payload: OrderCreate, user: CurrentUser, db: DbSession):
    order = await order_service.place_order(db, user, payload)
    return ApiResponse(message="Order placed", data=order_service.to_order_out(order))


@router.get("", response_model=ApiResponse[Page[OrderSummary]], summary="My orders")
async def list_my_orders(user: CurrentUser, db: DbSession, pagination: Pagination):
    base = select(Order).where(Order.user_id == user.id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = await db.execute(
        base.options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    return ApiResponse(
        data=Page(
            items=[OrderSummary.model_validate(o) for o in rows.scalars()],
            meta=PageMeta.build(pagination.page, pagination.limit, total),
        )
    )


@router.get("/{order_id}", response_model=ApiResponse[OrderOut], summary="Order detail with tracking timeline")
async def get_my_order(order_id: str, user: CurrentUser, db: DbSession):
    order = await order_service.get_order(db, order_id, user=user)
    return ApiResponse(data=order_service.to_order_out(order))


@router.post("/{order_id}/cancel", response_model=ApiResponse[OrderOut], summary="Cancel an order before it is packed")
async def cancel_my_order(order_id: str, user: CurrentUser, db: DbSession, payload: Optional[OrderCancel] = None):
    order = await order_service.cancel_order_by_customer(db, user, order_id, payload.reason if payload else None)
    return ApiResponse(message="Order cancelled", data=order_service.to_order_out(order))
