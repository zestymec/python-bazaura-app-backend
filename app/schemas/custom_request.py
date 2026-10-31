from datetime import datetime
from typing import List, Optional

from pydantic import Field, model_validator

from app.models.enums import CustomRequestType, DeliveryType
from app.schemas.common import BaseSchema
from app.schemas.user import AddressBase, AddressSnapshot


class DeliveryAddressIn(AddressBase):
    """Inline address. For gifts this is the recipient's address."""


class CustomRequestCreate(BaseSchema):
    request_type: CustomRequestType = CustomRequestType.CUSTOM_ITEM
    item_name: str = Field(..., min_length=2, max_length=200, examples=["Black oversized hoodie, size XL"])
    description: str = Field(..., min_length=5, max_length=2000)
    quantity: int = Field(1, ge=1, le=50)
    budget: Optional[int] = Field(None, ge=0, description="Expected price in PKR")
    reference_url: Optional[str] = Field(None, max_length=1000)
    image_urls: List[str] = Field(default_factory=list, max_length=5)
    delivery_type: DeliveryType = DeliveryType.STANDARD

    # Provide either a saved address id or an inline address (required for gifts to someone else).
    address_id: Optional[str] = None
    delivery_address: Optional[DeliveryAddressIn] = None

    gift_message: Optional[str] = Field(None, max_length=500)
    gift_wrap: bool = False
    hide_sender: bool = False
    deliver_on: Optional[datetime] = None

    @model_validator(mode="after")
    def _check_address(self) -> "CustomRequestCreate":
        if not self.address_id and not self.delivery_address:
            raise ValueError("Provide either addressId or deliveryAddress")
        if self.request_type == CustomRequestType.GIFT and not self.delivery_address and not self.address_id:
            raise ValueError("Gift requests need the recipient's delivery address")
        return self


class CustomRequestCancel(BaseSchema):
    reason: Optional[str] = Field(None, max_length=500)


class QuoteOut(BaseSchema):
    item_price: int
    delivery_fee: int
    extra_fee: int
    total: int
    notes: str
    valid_until: datetime


class CustomRequestOut(BaseSchema):
    id: str
    request_number: str
    request_type: str
    status: str
    item_name: str
    description: str
    quantity: int
    budget: Optional[int] = None
    reference_url: Optional[str] = None
    image_urls: List[str]
    delivery_type: str
    delivery_address: AddressSnapshot
    gift_message: Optional[str] = None
    gift_wrap: bool
    hide_sender: bool
    deliver_on: Optional[datetime] = None
    staff_note: Optional[str] = None
    quote: Optional[QuoteOut] = None
    order_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
