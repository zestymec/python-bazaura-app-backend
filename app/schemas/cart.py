from typing import List, Optional

from pydantic import Field

from app.models.enums import DeliveryType
from app.schemas.common import BaseSchema


class CartItemIn(BaseSchema):
    variant_id: str = Field(..., description="The size/colour variant being bought")
    quantity: int = Field(..., ge=1, le=20)


class CartQuoteRequest(BaseSchema):
    items: List[CartItemIn] = Field(..., min_length=1, max_length=50)
    voucher_code: Optional[str] = None
    delivery_type: DeliveryType = DeliveryType.STANDARD
    city: Optional[str] = Field(None, description="Delivery city; needed to check express eligibility")


class CartLine(BaseSchema):
    variant_id: str
    product_id: str
    product_slug: str
    title: str
    image_url: Optional[str] = None
    sku: str
    size: Optional[str] = None
    color: Optional[str] = None
    unit_price: int
    quantity: int
    line_total: int
    available_quantity: int


class CartIssue(BaseSchema):
    """A problem the customer must resolve before checkout (shown in the cart UI)."""

    code: str  # VARIANT_NOT_FOUND, OUT_OF_STOCK, INSUFFICIENT_STOCK, VOUCHER_INVALID, EXPRESS_UNAVAILABLE
    message: str
    variant_id: Optional[str] = None


class AppliedVoucher(BaseSchema):
    code: str
    description: str
    discount: int


class DeliveryOption(BaseSchema):
    type: DeliveryType
    label: str
    estimate: str
    fee: int
    available: bool


class CartQuote(BaseSchema):
    lines: List[CartLine]
    item_count: int
    subtotal: int
    discount: int
    delivery_fee: int
    extra_fee: int = 0
    total: int
    delivery_type: DeliveryType
    delivery_estimate: str
    delivery_options: List[DeliveryOption]
    free_shipping_threshold: int
    amount_to_free_shipping: int
    applied_voucher: Optional[AppliedVoucher] = None
    issues: List[CartIssue]
    can_checkout: bool
