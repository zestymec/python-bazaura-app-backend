from datetime import datetime
from typing import List, Optional

from pydantic import EmailStr, Field

from app.schemas.common import BaseSchema
from app.schemas.validators import NonEmptyStr, PakistanPhone


class AddressBase(BaseSchema):
    label: Optional[str] = Field(None, max_length=32, examples=["Home"])
    full_name: NonEmptyStr = Field(..., max_length=128)
    phone: PakistanPhone
    alternate_phone: Optional[PakistanPhone] = None
    address_line1: NonEmptyStr
    address_line2: Optional[str] = None
    area: NonEmptyStr = Field(..., max_length=128, examples=["Gulberg III"])
    city: NonEmptyStr = Field(..., max_length=64, examples=["Lahore"])
    postal_code: Optional[str] = Field(None, max_length=16)


class AddressSnapshot(BaseSchema):
    """Address frozen onto an order or custom request."""

    full_name: str
    phone: str
    alternate_phone: Optional[str] = None
    address_line1: str
    address_line2: Optional[str] = None
    area: str
    city: str
    postal_code: Optional[str] = None


class AddressCreate(AddressBase):
    is_default: bool = False


class AddressUpdate(BaseSchema):
    label: Optional[str] = Field(None, max_length=32)
    full_name: Optional[NonEmptyStr] = None
    phone: Optional[PakistanPhone] = None
    alternate_phone: Optional[PakistanPhone] = None
    address_line1: Optional[NonEmptyStr] = None
    address_line2: Optional[str] = None
    area: Optional[NonEmptyStr] = None
    city: Optional[NonEmptyStr] = None
    postal_code: Optional[str] = None
    is_default: Optional[bool] = None


class AddressOut(AddressBase):
    id: str
    is_default: bool
    is_express_eligible: bool


class UserOut(BaseSchema):
    id: str
    phone: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    city: Optional[str] = None
    role: str
    created_at: datetime


class UserProfile(UserOut):
    addresses: List[AddressOut] = []


class UserUpdate(BaseSchema):
    full_name: Optional[NonEmptyStr] = Field(None, max_length=128)
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None
    city: Optional[NonEmptyStr] = Field(None, max_length=64)
