"""
Bazaura.pk - Cart & Checkout Calculation Schemas
Validates items in customer shopping cart, applies vouchers, and calculates
subtotal, discounts, and delivery fees based on city and delivery speed.
"""

from typing import Any, Dict, List, Optional
from pydantic import Field
from app.schemas.base import BaseSchema
from app.schemas.product import VoucherResponse


class CartItemInput(BaseSchema):
    product_id: str
    quantity: int = Field(..., gt=0)
    selected_variants: Dict[str, Any] = Field(default_factory=dict)


class CartValidateRequest(BaseSchema):
    items: List[CartItemInput]
    voucher_code: Optional[str] = None
    delivery_type: str = Field("LAHORE_EXPRESS_2HR", examples=["LAHORE_EXPRESS_2HR", "NATIONWIDE_STANDARD"])
    city: str = Field("Lahore", examples=["Lahore", "Karachi", "Islamabad"])


class CartItemValidated(BaseSchema):
    product_id: str
    title: str
    quantity: int
    unit_price: int
    line_total: int
    image_url: Optional[str] = None
    in_stock: bool
    is_lahore_express_eligible: bool


class CartCalculationResult(BaseSchema):
    subtotal: int
    discount: int
    delivery_fee: int
    total: int
    item_count: int
    applied_voucher: Optional[VoucherResponse] = None
    delivery_type: str
    free_shipping_unlocked: bool
    free_shipping_threshold: int = 10000
    items: Optional[List[CartItemValidated]] = None
