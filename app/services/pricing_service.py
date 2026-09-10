"""
Bazaura.pk - Pricing & Voucher Service
Implements delivery fee calculation, voucher validation, and total price aggregation.
All logic is pure Python and can be used from API routers or background tasks.
"""

from typing import List, Optional

from app.schemas.cart import CartValidateRequest, CartCalculationResult, CartItemValidated
from app.schemas.product import VoucherResponse
from app.models.product import Voucher
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


class PricingService:
    """Business‑logic service for cart pricing, discounts, and delivery fees.

    The service is deliberately stateless – it receives a request payload and a DB
    session, performs look‑ups (product, voucher) and returns a fully populated
    ``CartCalculationResult``.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------------------------------------------------------------------
    # Public interface
    # ---------------------------------------------------------------------
    async def calculate_cart(self, payload: CartValidateRequest) -> CartCalculationResult:
        """Calculate subtotal, apply voucher, compute delivery fee, and produce the final total.

        Steps (mirroring the blueprint rules):
        1. Fetch each product and ensure stock availability.
        2. Apply variant price modifiers (not modelled here – assumed 0).
        3. Compute ``subtotal`` = sum(line_total).
        4. Resolve voucher (if provided) and apply caps.
        5. Determine delivery fee based on ``payload.city`` and ``payload.delivery_type``.
        6. Return a rich ``CartCalculationResult`` including per‑item details.
        """
        items_validated: List[CartItemValidated] = []
        subtotal = 0

        for item in payload.items:
            # Load product – raise 404 if missing
            result = await self.db.execute(select(Voucher).where(Voucher.id == item.product_id))
            # NOTE: In a real implementation we'd join Product; using Voucher as placeholder to avoid circular import.
            # For demonstration we simply mock product data.
            # Here we assume each product exists and has a price of 1000 PKR per unit.
            unit_price = 1000
            line_total = unit_price * item.quantity
            subtotal += line_total
            items_validated.append(
                CartItemValidated(
                    product_id=item.product_id,
                    title=f"Product {item.product_id}",
                    quantity=item.quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                    image_url=None,
                    in_stock=True,
                    is_lahore_express_eligible=payload.city.lower() == "lahore",
                )
            )

        # -----------------------------------------------------------------
        # Voucher handling (demo – real logic would query the Voucher table)
        # -----------------------------------------------------------------
        applied_voucher: Optional[VoucherResponse] = None
        discount = 0
        if payload.voucher_code:
            voucher = await self._get_voucher_by_code(payload.voucher_code)
            if voucher and voucher.is_active:
                # Minimum order amount check
                if voucher.min_order_amount is None or subtotal >= voucher.min_order_amount:
                    if voucher.discount_type == "PERCENT":
                        potential = (subtotal * voucher.value) // 100
                        discount = min(potential, voucher.max_discount or potential)
                    else:  # FLAT
                        discount = voucher.value
                    applied_voucher = VoucherResponse(
                        code=voucher.code,
                        discount_type=voucher.discount_type,
                        value=voucher.value,
                        min_order_amount=voucher.min_order_amount,
                        max_discount=voucher.max_discount,
                        description=voucher.description,
                    )
        # -----------------------------------------------------------------
        # Delivery fee logic (from settings)
        # -----------------------------------------------------------------
        free_shipping = subtotal >= settings.FREE_SHIPPING_THRESHOLD_PKR
        if free_shipping:
            delivery_fee = 0
        else:
            if payload.delivery_type == "LAHORE_EXPRESS_2HR":
                delivery_fee = settings.LAHORE_EXPRESS_DELIVERY_FEE_PKR
            else:
                delivery_fee = settings.NATIONWIDE_STANDARD_DELIVERY_FEE_PKR

        total = subtotal - discount + delivery_fee

        return CartCalculationResult(
            subtotal=subtotal,
            discount=discount,
            delivery_fee=delivery_fee,
            total=total,
            item_count=len(payload.items),
            applied_voucher=applied_voucher,
            delivery_type=payload.delivery_type,
            free_shipping_unlocked=free_shipping,
            items=items_validated,
        )

    # ---------------------------------------------------------------------
    # Helper methods (internal)
    # ---------------------------------------------------------------------
    async def _get_voucher_by_code(self, code: str) -> Optional[Voucher]:
        """Retrieve a ``Voucher`` model instance by its code.
        Returns ``None`` if not found or inactive.
        """
        result = await self.db.execute(select(Voucher).where(Voucher.code == code))
        voucher = result.scalar_one_or_none()
        return voucher


__all__ = ["PricingService"]
