"""
Bazaura.pk - Bazaura Sourcing Concierge Schemas
Models the custom procurement request workflow, quotation generation,
timeline tracking, and quote acceptance.
"""

from typing import List, Optional
from datetime import datetime
from pydantic import Field
from app.schemas.base import BaseSchema


class CustomItemRequestCreate(BaseSchema):
    item_name: str
    category: str
    brand_or_model: Optional[str] = None
    expected_price: Optional[int] = None
    reference_url: Optional[str] = None
    description: str
    image_uris: List[str] = Field(default_factory=list)
    urgency: str = Field("LAHORE_2HR_EXPRESS", examples=["LAHORE_2HR_EXPRESS", "STANDARD_NATIONWIDE"])
    contact_phone: str
    delivery_address: str
    city: str = Field("Lahore", examples=["Lahore", "Karachi", "Islamabad"])


class SourcingQuoteResponse(BaseSchema):
    quoted_price: int
    estimated_delivery_hours: int = 2
    delivery_type: str = "LAHORE_EXPRESS_2HR"
    notes: str
    valid_until: datetime


class SourcingQuoteCreate(BaseSchema):
    quoted_price: int = Field(..., gt=0)
    estimated_delivery_hours: int = Field(2, ge=1)
    delivery_type: str = Field("LAHORE_EXPRESS_2HR")
    notes: str
    valid_days: int = Field(2, ge=1)


class RequestTimelineStep(BaseSchema):
    status: str
    label: str
    timestamp: str
    description: str


class CustomItemRequestResponse(BaseSchema):
    id: str
    item_name: str
    category: Optional[str] = None
    status: str
    urgency: str
    created_at: datetime
    brand_or_model: Optional[str] = None
    expected_price: Optional[int] = None
    reference_url: Optional[str] = None
    description: Optional[str] = None
    image_uris: List[str] = []
    contact_phone: Optional[str] = None
    delivery_address: Optional[str] = None
    city: Optional[str] = None
    quote: Optional[SourcingQuoteResponse] = None
    status_timeline: List[RequestTimelineStep] = []


class AcceptQuoteRequest(BaseSchema):
    payment_method: str = Field("CASH_ON_DELIVERY", examples=["CASH_ON_DELIVERY", "JAZZCASH", "EASYPAISA", "DEBIT_CREDIT_CARD"])


class AcceptQuoteResponseData(BaseSchema):
    id: str
    status: str
    order_id: str
