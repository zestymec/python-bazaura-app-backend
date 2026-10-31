"""
Cart pricing. The single source of truth for subtotal, voucher discount,
delivery fee and total — used both by the cart screen and by order placement,
so what the customer sees is exactly what the order will charge.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.catalog import ProductVariant
from app.models.enums import DeliveryType, DiscountType
from app.models.voucher import Voucher
from app.schemas.cart import AppliedVoucher, CartIssue, CartItemIn, CartLine, CartQuote
from app.services import delivery


@dataclass
class PricedCart:
    quote: CartQuote
    variants: Dict[str, ProductVariant] = field(default_factory=dict)
    voucher: Optional[Voucher] = None


def merge_items(items: Sequence[CartItemIn]) -> Dict[str, int]:
    """Combines duplicate lines for the same variant."""
    merged: Dict[str, int] = {}
    for item in items:
        merged[item.variant_id] = merged.get(item.variant_id, 0) + item.quantity
    return merged


async def price_cart(
    db: AsyncSession,
    items: Sequence[CartItemIn],
    *,
    voucher_code: Optional[str],
    delivery_type: DeliveryType,
    city: Optional[str],
    lock_stock: bool = False,
) -> PricedCart:
    quantities = merge_items(items)
    query = (
        select(ProductVariant)
        .options(selectinload(ProductVariant.product))
        .where(ProductVariant.id.in_(quantities.keys()))
    )
    if lock_stock:
        query = query.with_for_update()
    variants = {v.id: v for v in (await db.execute(query)).scalars().all()}

    lines: List[CartLine] = []
    issues: List[CartIssue] = []
    for variant_id, quantity in quantities.items():
        variant = variants.get(variant_id)
        if variant is None or not variant.is_active or not variant.product.is_active:
            issues.append(
                CartIssue(code="VARIANT_NOT_FOUND", message="This item is no longer available", variant_id=variant_id)
            )
            variants.pop(variant_id, None)
            continue

        product = variant.product
        if variant.stock_quantity <= 0:
            issues.append(
                CartIssue(code="OUT_OF_STOCK", message=f"{product.title} is out of stock", variant_id=variant_id)
            )
        elif variant.stock_quantity < quantity:
            issues.append(
                CartIssue(
                    code="INSUFFICIENT_STOCK",
                    message=f"Only {variant.stock_quantity} left of {product.title}",
                    variant_id=variant_id,
                )
            )
        lines.append(
            CartLine(
                variant_id=variant.id,
                product_id=product.id,
                product_slug=product.slug,
                title=product.title,
                image_url=product.primary_image,
                sku=variant.sku,
                size=variant.size,
                color=variant.color,
                unit_price=variant.price,
                quantity=quantity,
                line_total=variant.price * quantity,
                available_quantity=variant.stock_quantity,
            )
        )

    subtotal = sum(line.line_total for line in lines)

    voucher, applied_voucher, discount = None, None, 0
    if voucher_code:
        voucher, discount, voucher_issue = await _apply_voucher(db, voucher_code, subtotal)
        if voucher_issue:
            issues.append(voucher_issue)
        elif voucher:
            applied_voucher = AppliedVoucher(code=voucher.code, description=voucher.description, discount=discount)

    all_express = all(v.product.is_express_eligible for v in variants.values())
    express_blocker = delivery.express_unavailable_reason(city, all_express)
    if delivery_type == DeliveryType.EXPRESS and express_blocker:
        issues.append(CartIssue(code="EXPRESS_UNAVAILABLE", message=express_blocker))

    fee = delivery.delivery_fee(delivery_type, subtotal)
    quote = CartQuote(
        lines=lines,
        item_count=sum(line.quantity for line in lines),
        subtotal=subtotal,
        discount=discount,
        delivery_fee=fee,
        total=subtotal - discount + fee,
        delivery_type=delivery_type,
        delivery_estimate=delivery.delivery_estimate(delivery_type),
        delivery_options=delivery.delivery_options(subtotal, express_available=express_blocker is None),
        free_shipping_threshold=settings.FREE_SHIPPING_THRESHOLD_PKR,
        amount_to_free_shipping=max(settings.FREE_SHIPPING_THRESHOLD_PKR - subtotal, 0),
        applied_voucher=applied_voucher,
        issues=issues,
        can_checkout=bool(lines) and not issues,
    )
    return PricedCart(quote=quote, variants=variants, voucher=voucher if applied_voucher else None)


async def _apply_voucher(db: AsyncSession, code: str, subtotal: int):
    voucher = (await db.execute(select(Voucher).where(Voucher.code == code.strip().upper()))).scalar_one_or_none()
    if voucher is None:
        return None, 0, CartIssue(code="VOUCHER_INVALID", message="Voucher code not found")

    reason = voucher.unavailable_reason()
    if reason:
        return None, 0, CartIssue(code="VOUCHER_INVALID", message=reason)
    if voucher.min_order_amount and subtotal < voucher.min_order_amount:
        short_by = voucher.min_order_amount - subtotal
        return None, 0, CartIssue(code="VOUCHER_INVALID", message=f"Add Rs. {short_by:,} more to use this voucher")

    if voucher.discount_type == DiscountType.PERCENT:
        discount = subtotal * voucher.value // 100
        if voucher.max_discount is not None:
            discount = min(discount, voucher.max_discount)
    else:
        discount = voucher.value
    return voucher, min(discount, subtotal), None
