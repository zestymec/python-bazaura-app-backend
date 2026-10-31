r"""
Custom requests ("arrange this for me" / "send a gift"):

    SUBMITTED -> IN_REVIEW -> QUOTED -> CONFIRMED (order created)
                     \-> UNAVAILABLE        \-> CANCELLED (by customer)
"""

from datetime import timedelta
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.base import utcnow
from app.models.custom_request import CustomRequest, CustomRequestQuote
from app.models.enums import CustomRequestStatus, CustomRequestType, DeliveryType, OrderSource, OrderStatus
from app.models.order import Order, OrderItem, OrderStatusEvent
from app.models.user import Address, User
from app.schemas.admin import QuoteCreate
from app.schemas.custom_request import CustomRequestCreate
from app.services import delivery
from app.services.order_service import generate_unique_reference

LOAD_OPTIONS = (selectinload(CustomRequest.quote),)
OPEN_STATUSES = {CustomRequestStatus.SUBMITTED, CustomRequestStatus.IN_REVIEW, CustomRequestStatus.QUOTED}


async def create_request(db: AsyncSession, user: User, payload: CustomRequestCreate) -> CustomRequest:
    if payload.delivery_address:
        address_snapshot = payload.delivery_address.model_dump()
    else:
        address = await db.get(Address, payload.address_id)
        if address is None or address.user_id != user.id:
            raise NotFoundError("Address not found", code="ADDRESS_NOT_FOUND")
        address_snapshot = address.snapshot()

    if payload.delivery_type == DeliveryType.EXPRESS and not settings.is_express_city(address_snapshot["city"]):
        raise BadRequestError(
            delivery.express_unavailable_reason(address_snapshot["city"], True) or "Express delivery unavailable",
            code="EXPRESS_UNAVAILABLE",
        )

    is_gift = payload.request_type == CustomRequestType.GIFT
    request = CustomRequest(
        request_number=await generate_unique_reference(db, CustomRequest, CustomRequest.request_number, "RQ"),
        user_id=user.id,
        request_type=payload.request_type,
        status=CustomRequestStatus.SUBMITTED,
        item_name=payload.item_name,
        description=payload.description,
        quantity=payload.quantity,
        budget=payload.budget,
        reference_url=payload.reference_url,
        image_urls=payload.image_urls,
        delivery_type=payload.delivery_type,
        delivery_address=address_snapshot,
        gift_message=payload.gift_message if is_gift else None,
        gift_wrap=payload.gift_wrap if is_gift else False,
        hide_sender=payload.hide_sender if is_gift else False,
        deliver_on=payload.deliver_on,
    )
    db.add(request)
    await db.commit()
    return await get_request(db, request.id)


async def get_request(db: AsyncSession, request_id: str, *, user: Optional[User] = None) -> CustomRequest:
    request = (
        await db.execute(select(CustomRequest).options(*LOAD_OPTIONS).where(CustomRequest.id == request_id))
    ).scalar_one_or_none()
    if request is None or (user is not None and request.user_id != user.id):
        raise NotFoundError("Request not found", code="REQUEST_NOT_FOUND")
    return request


async def list_requests(
    db: AsyncSession,
    *,
    user: Optional[User] = None,
    status: Optional[CustomRequestStatus] = None,
    offset: int = 0,
    limit: int = 20,
) -> List[CustomRequest]:
    query = select(CustomRequest).options(*LOAD_OPTIONS).order_by(CustomRequest.created_at.desc())
    if user is not None:
        query = query.where(CustomRequest.user_id == user.id)
    if status:
        query = query.where(CustomRequest.status == status)
    return list((await db.execute(query.offset(offset).limit(limit))).scalars().all())


async def cancel_request(db: AsyncSession, user: User, request_id: str, reason: Optional[str]) -> CustomRequest:
    request = await get_request(db, request_id, user=user)
    if request.status not in OPEN_STATUSES:
        raise ConflictError("This request can no longer be cancelled", code="REQUEST_NOT_CANCELLABLE")
    request.status = CustomRequestStatus.CANCELLED
    if reason:
        request.staff_note = f"Cancelled by customer: {reason}"
    await db.commit()
    return await get_request(db, request.id)


async def accept_quote(db: AsyncSession, user: User, request_id: str) -> CustomRequest:
    request = await get_request(db, request_id, user=user)
    quote = request.quote
    if request.status != CustomRequestStatus.QUOTED or quote is None:
        raise ConflictError("There is no quote to accept for this request", code="NO_ACTIVE_QUOTE")
    if quote.valid_until < utcnow():
        raise ConflictError("This quote has expired. Please ask for a new quote", code="QUOTE_EXPIRED")

    order = Order(
        order_number=await generate_unique_reference(db, Order, Order.order_number, "BZ"),
        user_id=user.id,
        source=OrderSource.CUSTOM_REQUEST,
        status=OrderStatus.CONFIRMED,
        subtotal=quote.item_price,
        delivery_fee=quote.delivery_fee,
        extra_fee=quote.extra_fee,
        total=quote.total,
        delivery_type=request.delivery_type,
        delivery_estimate=delivery.delivery_estimate(DeliveryType(request.delivery_type)),
        shipping_address=request.delivery_address,
        customer_note=_order_note(request),
    )
    order.items.append(
        OrderItem(
            title=request.item_name,
            image_url=request.image_urls[0] if request.image_urls else None,
            unit_price=quote.item_price // request.quantity,  # exact: quotes are unit_price * quantity
            quantity=request.quantity,
        )
    )
    order.status_history.append(
        OrderStatusEvent(
            status=OrderStatus.CONFIRMED, note=f"From request {request.request_number}", created_by_id=user.id
        )
    )
    db.add(order)
    await db.flush()

    request.status = CustomRequestStatus.CONFIRMED
    request.order_id = order.id
    await db.commit()
    return await get_request(db, request.id)


# --- Staff -------------------------------------------------------------------
async def send_quote(db: AsyncSession, staff: User, request_id: str, payload: QuoteCreate) -> CustomRequest:
    request = await get_request(db, request_id)
    if request.status not in OPEN_STATUSES:
        raise ConflictError("Only open requests can be quoted", code="REQUEST_CLOSED")

    delivery_type = DeliveryType(request.delivery_type)
    item_price = payload.unit_price * request.quantity
    default_delivery_fee = delivery.delivery_fee(delivery_type, item_price)
    default_extra_fee = settings.GIFT_WRAP_FEE_PKR if request.gift_wrap else 0
    values = dict(
        item_price=item_price,
        delivery_fee=payload.delivery_fee if payload.delivery_fee is not None else default_delivery_fee,
        extra_fee=payload.extra_fee if payload.extra_fee is not None else default_extra_fee,
        notes=payload.notes,
        valid_until=utcnow() + timedelta(days=payload.valid_days or settings.CUSTOM_REQUEST_QUOTE_VALID_DAYS),
        created_by_id=staff.id,
    )
    if request.quote:
        for key, value in values.items():
            setattr(request.quote, key, value)
    else:
        request.quote = CustomRequestQuote(**values)
    request.status = CustomRequestStatus.QUOTED
    await db.commit()
    return await get_request(db, request.id)


async def update_status_by_staff(
    db: AsyncSession, request_id: str, status: CustomRequestStatus, staff_note: Optional[str]
) -> CustomRequest:
    if status not in (CustomRequestStatus.IN_REVIEW, CustomRequestStatus.UNAVAILABLE):
        raise BadRequestError("Staff can only set IN_REVIEW or UNAVAILABLE here", code="INVALID_STATUS")
    request = await get_request(db, request_id)
    if request.status not in OPEN_STATUSES:
        raise ConflictError("This request is already closed", code="REQUEST_CLOSED")
    request.status = status
    if staff_note is not None:
        request.staff_note = staff_note
    await db.commit()
    return await get_request(db, request.id)


def _order_note(request: CustomRequest) -> Optional[str]:
    if request.request_type != CustomRequestType.GIFT:
        return None
    parts = ["GIFT ORDER"]
    if request.gift_wrap:
        parts.append("gift wrap")
    if request.hide_sender:
        parts.append("hide sender name")
    if request.gift_message:
        parts.append(f"message: {request.gift_message}")
    return " | ".join(parts)
