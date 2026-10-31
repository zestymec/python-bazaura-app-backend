from datetime import datetime
from typing import List, Optional

from pydantic import Field

from app.models.enums import DeliveryType
from app.schemas.cart import CartItemIn
from app.schemas.common import BaseSchema
from app.schemas.user import AddressSnapshot


class OrderCreate(BaseSchema):
    """
    Prices are never accepted from the client — the server recalculates
    everything from the database. Payment is Cash on Delivery.
    """

    items: List[CartItemIn] = Field(..., min_length=1, max_length=50)
    address_id: str
    delivery_type: DeliveryType = DeliveryType.STANDARD
    voucher_code: Optional[str] = None
    customer_note: Optional[str] = Field(None, max_length=500)


class OrderCancel(BaseSchema):
    reason: Optional[str] = Field(None, max_length=500)


class OrderItemOut(BaseSchema):
    id: str
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    title: str
    product_slug: Optional[str] = None
    image_url: Optional[str] = None
    sku: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    unit_price: int
    quantity: int
    line_total: int


class OrderStatusEventOut(BaseSchema):
    status: str
    note: Optional[str] = None
    created_at: datetime


class TimelineStep(BaseSchema):
    status: str
    label: str
    is_completed: bool
    is_current: bool
    completed_at: Optional[datetime] = None


class OrderSummary(BaseSchema):
    id: str
    order_number: str
    status: str
    source: str
    total: int
    item_count: int
    delivery_type: str
    created_at: datetime


class OrderOut(OrderSummary):
    subtotal: int
    discount: int
    delivery_fee: int
    extra_fee: int
    voucher_code: Optional[str] = None
    payment_method: str = "CASH_ON_DELIVERY"
    delivery_estimate: str
    shipping_address: AddressSnapshot
    customer_note: Optional[str] = None
    cancel_reason: Optional[str] = None
    can_cancel: bool
    items: List[OrderItemOut]
    timeline: List[TimelineStep]
    status_history: List[OrderStatusEventOut]
