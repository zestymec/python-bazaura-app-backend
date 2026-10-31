"""
Staff: order management and custom request handling.
"""

from typing import List, Optional

from fastapi import APIRouter, Query
from sqlalchemy import func, or_, select

from app.api.deps import DbSession, Pagination, StaffUser
from app.models.custom_request import CustomRequest
from app.models.enums import CustomRequestStatus, OrderStatus
from app.models.order import Order
from app.models.user import User
from app.schemas.admin import (
    AdminCustomRequestOut,
    AdminOrderOut,
    CustomRequestStatusUpdate,
    OrderStatusUpdate,
    QuoteCreate,
)
from app.schemas.common import ApiResponse, Page, PageMeta
from app.services import custom_request_service, order_service

router = APIRouter()


def _admin_order(order: Order) -> AdminOrderOut:
    return order_service.to_order_out(
        order,
        schema=AdminOrderOut,
        user_id=order.user_id,
        customer_phone=order.user.phone if order.user else None,
        customer_name=order.user.full_name if order.user else None,
    )


@router.get("/orders", response_model=ApiResponse[Page[AdminOrderOut]], tags=["Admin: orders"])
async def list_orders(
    _: StaffUser,
    db: DbSession,
    pagination: Pagination,
    status: Optional[OrderStatus] = None,
    q: Optional[str] = Query(None, description="Order number or customer phone"),
):
    query = select(Order).join(User)
    if status:
        query = query.where(Order.status == status)
    if q:
        query = query.where(or_(Order.order_number.ilike(f"%{q}%"), User.phone.like(f"%{q.lstrip('0')}%")))
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = await db.execute(
        query.options(*order_service.ORDER_LOAD_OPTIONS)
        .order_by(Order.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    return ApiResponse(
        data=Page(
            items=[_admin_order(o) for o in rows.scalars()],
            meta=PageMeta.build(pagination.page, pagination.limit, total),
        )
    )


@router.get("/orders/{order_id}", response_model=ApiResponse[AdminOrderOut], tags=["Admin: orders"])
async def get_order(order_id: str, _: StaffUser, db: DbSession):
    return ApiResponse(data=_admin_order(await order_service.get_order(db, order_id)))


@router.patch(
    "/orders/{order_id}/status",
    response_model=ApiResponse[AdminOrderOut],
    tags=["Admin: orders"],
    summary="Move an order forward (PLACED → CONFIRMED → PACKED → SHIPPED → DELIVERED) or cancel it",
)
async def update_order_status(order_id: str, payload: OrderStatusUpdate, staff: StaffUser, db: DbSession):
    order = await order_service.update_status_by_staff(db, staff, order_id, payload.status, payload.note)
    return ApiResponse(message=f"Order marked {order.status}", data=_admin_order(order))


# --- Custom requests ---------------------------------------------------------
def _admin_request(request: CustomRequest) -> AdminCustomRequestOut:
    return AdminCustomRequestOut.model_validate(request)


@router.get(
    "/custom-requests", response_model=ApiResponse[List[AdminCustomRequestOut]], tags=["Admin: custom requests"]
)
async def list_custom_requests(
    _: StaffUser, db: DbSession, pagination: Pagination, status: Optional[CustomRequestStatus] = None
):
    requests = await custom_request_service.list_requests(
        db, status=status, offset=pagination.offset, limit=pagination.limit
    )
    return ApiResponse(data=[_admin_request(r) for r in requests])


@router.get(
    "/custom-requests/{request_id}", response_model=ApiResponse[AdminCustomRequestOut], tags=["Admin: custom requests"]
)
async def get_custom_request(request_id: str, _: StaffUser, db: DbSession):
    return ApiResponse(data=_admin_request(await custom_request_service.get_request(db, request_id)))


@router.post(
    "/custom-requests/{request_id}/quote",
    response_model=ApiResponse[AdminCustomRequestOut],
    tags=["Admin: custom requests"],
    summary="Send (or replace) a price quote",
)
async def send_quote(request_id: str, payload: QuoteCreate, staff: StaffUser, db: DbSession):
    request = await custom_request_service.send_quote(db, staff, request_id, payload)
    return ApiResponse(message="Quote sent", data=_admin_request(request))


@router.patch(
    "/custom-requests/{request_id}/status",
    response_model=ApiResponse[AdminCustomRequestOut],
    tags=["Admin: custom requests"],
)
async def update_custom_request_status(
    request_id: str, payload: CustomRequestStatusUpdate, _: StaffUser, db: DbSession
):
    request = await custom_request_service.update_status_by_staff(db, request_id, payload.status, payload.staff_note)
    return ApiResponse(message=f"Request marked {request.status}", data=_admin_request(request))
