"""
Bazaura.pk - Orders & Tracking Timeline Schemas
Defines request payloads for placing quick-commerce orders and response models
including frozen shipping snapshots, payment methods, and live fulfillment timeline steps.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import Field
from app.schemas.base import BaseSchema
from app.schemas.user import ShippingAddressResponse


class OrderItemInput(BaseSchema):
    product_id: str
    quantity: int = Field(..., gt=0)
    selected_variants: Dict[str, Any] = Field(default_factory=dict)
    unit_price: Optional[int] = None


class OrderCreateRequest(BaseSchema):
    items: List[OrderItemInput]
    subtotal: Optional[int] = None
    discount: Optional[int] = 0
    delivery_fee: Optional[int] = None
    total: Optional[int] = None
    delivery_type: str = Field("LAHORE_EXPRESS_2HR", examples=["LAHORE_EXPRESS_2HR", "NATIONWIDE_STANDARD"])
    shipping_address_id: str
    payment_method: str = Field("CASH_ON_DELIVERY", examples=["CASH_ON_DELIVERY", "JAZZCASH", "EASYPAISA", "DEBIT_CREDIT_CARD"])
    voucher_code: Optional[str] = None


class OrderTimelineStep(BaseSchema):
    status: str
    title: str
    description: str
    timestamp: str
    is_completed: bool


class OrderItemDetail(BaseSchema):
    id: str
    product_id: Optional[str] = None
    product_snapshot: Dict[str, Any]
    quantity: int
    unit_price: int
    selected_variants: Dict[str, Any] = {}


class OrderResponse(BaseSchema):
    id: str
    order_number: str
    status: str
    subtotal: int
    discount: int
    delivery_fee: int
    total: int
    delivery_type: str
    estimated_delivery_text: str
    payment_method: str
    payment_status: str
    payment_reference: Optional[str] = None
    created_at: datetime
    shipping_address: Optional[Dict[str, Any]] = None
    timeline: List[OrderTimelineStep] = []
    items: Optional[List[OrderItemDetail]] = None
