"""
Order lifecycle: placement (stock reservation inside one transaction),
customer cancellation, staff status updates and the tracking timeline.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.base import utcnow
from app.models.catalog import ProductVariant
from app.models.enums import DeliveryType, OrderSource, OrderStatus
from app.models.order import Order, OrderItem, OrderStatusEvent
from app.models.user import Address, User
from app.models.voucher import Voucher
from app.schemas.order import OrderCreate, OrderItemOut, OrderOut, OrderStatusEventOut, TimelineStep
from app.services import pricing_service
from app.utils.text import human_reference

ORDER_LOAD_OPTIONS = (selectinload(Order.items), selectinload(Order.status_history), selectinload(Order.user))

# Which status may follow which. Anything else is rejected.
ALLOWED_TRANSITIONS = {
    OrderStatus.PLACED: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PACKED, OrderStatus.CANCELLED},
    OrderStatus.PACKED: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED, OrderStatus.RETURNED},
    OrderStatus.DELIVERED: {OrderStatus.RETURNED},
    OrderStatus.CANCELLED: set(),
    OrderStatus.RETURNED: set(),
}
CUSTOMER_CANCELLABLE = {OrderStatus.PLACED, OrderStatus.CONFIRMED}
RESTOCK_ON = {OrderStatus.CANCELLED}

TIMELINE_STEPS = [
    (OrderStatus.PLACED, "Order placed"),
    (OrderStatus.CONFIRMED, "Order confirmed"),
    (OrderStatus.PACKED, "Packed"),
    (OrderStatus.SHIPPED, "Out for delivery"),
    (OrderStatus.DELIVERED, "Delivered"),
]


async def generate_unique_reference(db: AsyncSession, model, column, prefix: str) -> str:
    for _ in range(10):
        reference = human_reference(prefix)
        if (await db.execute(select(model.id).where(column == reference))).first() is None:
            return reference
    raise ConflictError("Could not generate a unique reference, please retry")


async def place_order(db: AsyncSession, user: User, payload: OrderCreate) -> Order:
    address = await db.get(Address, payload.address_id)
    if address is None or address.user_id != user.id:
        raise NotFoundError("Address not found", code="ADDRESS_NOT_FOUND")

    priced = await pricing_service.price_cart(
        db,
        payload.items,
        voucher_code=payload.voucher_code,
        delivery_type=payload.delivery_type,
        city=address.city,
        lock_stock=True,
    )
    quote = priced.quote
    if not quote.can_checkout:
        raise BadRequestError(
            "Your cart needs attention before checkout",
            code="CART_INVALID",
            details=[issue.model_dump(by_alias=True) for issue in quote.issues],
        )

    order = Order(
        order_number=await generate_unique_reference(db, Order, Order.order_number, "BZ"),
        user_id=user.id,
        source=OrderSource.CATALOG,
        status=OrderStatus.PLACED,
        subtotal=quote.subtotal,
        discount=quote.discount,
        delivery_fee=quote.delivery_fee,
        total=quote.total,
        voucher_code=priced.voucher.code if priced.voucher else None,
        delivery_type=quote.delivery_type,
        delivery_estimate=quote.delivery_estimate,
        shipping_address=address.snapshot(),
        customer_note=payload.customer_note,
    )
    for line in quote.lines:
        variant = priced.variants[line.variant_id]
        variant.stock_quantity -= line.quantity
        variant.product.sold_count += line.quantity
        order.items.append(
            OrderItem(
                product_id=line.product_id,
                variant_id=line.variant_id,
                title=line.title,
                product_slug=line.product_slug,
                image_url=line.image_url,
                sku=line.sku,
                size=line.size,
                color=line.color,
                unit_price=line.unit_price,
                quantity=line.quantity,
            )
        )
    order.status_history.append(OrderStatusEvent(status=OrderStatus.PLACED, created_by_id=user.id))
    if priced.voucher:
        priced.voucher.used_count += 1

    db.add(order)
    await db.commit()
    return await get_order(db, order.id)


async def get_order(db: AsyncSession, order_id: str, *, user: Optional[User] = None) -> Order:
    order = (
        await db.execute(select(Order).options(*ORDER_LOAD_OPTIONS).where(Order.id == order_id))
    ).scalar_one_or_none()
    if order is None or (user is not None and order.user_id != user.id):
        raise NotFoundError("Order not found", code="ORDER_NOT_FOUND")
    return order


async def cancel_order_by_customer(db: AsyncSession, user: User, order_id: str, reason: Optional[str]) -> Order:
    order = await get_order(db, order_id, user=user)
    if order.status not in CUSTOMER_CANCELLABLE:
        raise ConflictError("This order can no longer be cancelled", code="ORDER_NOT_CANCELLABLE")
    await _apply_status(db, order, OrderStatus.CANCELLED, note=reason, actor_id=user.id)
    order.cancel_reason = reason
    await db.commit()
    return await get_order(db, order.id)


async def update_status_by_staff(
    db: AsyncSession, staff: User, order_id: str, new_status: OrderStatus, note: Optional[str]
) -> Order:
    order = await get_order(db, order_id)
    if new_status not in ALLOWED_TRANSITIONS[OrderStatus(order.status)]:
        raise ConflictError(
            f"Cannot move an order from {order.status} to {new_status}", code="INVALID_STATUS_TRANSITION"
        )
    await _apply_status(db, order, new_status, note=note, actor_id=staff.id)
    if new_status == OrderStatus.CANCELLED:
        order.cancel_reason = note
    await db.commit()
    return await get_order(db, order.id)


async def _apply_status(
    db: AsyncSession, order: Order, new_status: OrderStatus, *, note: Optional[str], actor_id: str
) -> None:
    order.status = new_status
    if new_status == OrderStatus.DELIVERED:
        order.delivered_at = utcnow()
    order.status_history.append(OrderStatusEvent(status=new_status, note=note, created_by_id=actor_id))

    if new_status in RESTOCK_ON:
        await _restock(db, order)
        if order.voucher_code:
            voucher = (await db.execute(select(Voucher).where(Voucher.code == order.voucher_code))).scalar_one_or_none()
            if voucher and voucher.used_count > 0:
                voucher.used_count -= 1


async def _restock(db: AsyncSession, order: Order) -> None:
    variant_ids = [item.variant_id for item in order.items if item.variant_id]
    if not variant_ids:
        return
    variants = {
        v.id: v
        for v in (
            await db.execute(
                select(ProductVariant)
                .options(selectinload(ProductVariant.product))
                .where(ProductVariant.id.in_(variant_ids))
                .with_for_update()
            )
        ).scalars()
    }
    for item in order.items:
        variant = variants.get(item.variant_id)
        if variant:
            variant.stock_quantity += item.quantity
            variant.product.sold_count = max(variant.product.sold_count - item.quantity, 0)


# --- Presentation ------------------------------------------------------------
def build_timeline(order: Order) -> List[TimelineStep]:
    reached = {event.status: event.created_at for event in order.status_history}
    steps = list(TIMELINE_STEPS)
    if order.delivery_type != DeliveryType.EXPRESS:
        steps[3] = (OrderStatus.SHIPPED, "Shipped")

    timeline = []
    for status, label in steps:
        if order.status in (OrderStatus.CANCELLED, OrderStatus.RETURNED) and status not in reached:
            continue
        timeline.append(
            TimelineStep(
                status=status,
                label=label,
                is_completed=status in reached,
                is_current=order.status == status,
                completed_at=reached.get(status),
            )
        )
    if order.status in (OrderStatus.CANCELLED, OrderStatus.RETURNED):
        label = "Cancelled" if order.status == OrderStatus.CANCELLED else "Returned"
        timeline.append(
            TimelineStep(
                status=order.status,
                label=label,
                is_completed=True,
                is_current=True,
                completed_at=reached.get(order.status),
            )
        )
    return timeline


def to_order_out(order: Order, schema=OrderOut, **extra) -> OrderOut:
    return schema(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        source=order.source,
        total=order.total,
        item_count=order.item_count,
        delivery_type=order.delivery_type,
        created_at=order.created_at,
        subtotal=order.subtotal,
        discount=order.discount,
        delivery_fee=order.delivery_fee,
        extra_fee=order.extra_fee,
        voucher_code=order.voucher_code,
        delivery_estimate=order.delivery_estimate,
        shipping_address=order.shipping_address,
        customer_note=order.customer_note,
        cancel_reason=order.cancel_reason,
        can_cancel=order.status in CUSTOMER_CANCELLABLE,
        items=[OrderItemOut.model_validate(item) for item in order.items],
        timeline=build_timeline(order),
        status_history=[OrderStatusEventOut.model_validate(event) for event in order.status_history],
        **extra,
    )
