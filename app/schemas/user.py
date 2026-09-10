"""
Bazaura.pk - User & Address Pydantic v2 Schemas
Covers OTP authentication, token responses, profile mutations, and shipping addresses.
"""

from typing import List, Optional
from pydantic import Field
from app.schemas.base import BaseSchema


class OTPRequest(BaseSchema):
    phone: str = Field(..., examples=["03001234567", "+923001234567"])


class OTPRequestData(BaseSchema):
    expires_in_seconds: int = 120
    resend_available_in_seconds: int = 60


class OTPVerifyRequest(BaseSchema):
    phone: str = Field(..., examples=["03001234567"])
    otp_code: str = Field(..., min_length=4, max_length=6, examples=["4821"])
    full_name: Optional[str] = Field(None, examples=["Muhammad Ali"])


class RefreshTokenRequest(BaseSchema):
    refresh_token: str


class ShippingAddressCreate(BaseSchema):
    full_name: str
    phone: str
    alternate_phone: Optional[str] = None
    address_line1: str
    address_line2: Optional[str] = None
    area: str
    city: str
    postal_code: Optional[str] = None
    is_default: bool = False


class ShippingAddressResponse(BaseSchema):
    id: str
    full_name: str
    phone: str
    alternate_phone: Optional[str] = None
    address_line1: str
    address_line2: Optional[str] = None
    area: str
    city: str
    postal_code: Optional[str] = None
    is_lahore: bool
    is_default: bool


class UserPublic(BaseSchema):
    id: str
    full_name: str
    email: Optional[str] = None
    phone: str
    avatar_url: Optional[str] = None
    selected_city: str
    is_lahore_express_eligible: bool
    member_since: str
    default_address_id: Optional[str] = None


class UserProfileDetail(UserPublic):
    addresses: List[ShippingAddressResponse] = []


class UserProfileUpdate(BaseSchema):
    full_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None


class UserCityUpdate(BaseSchema):
    city: str = Field(..., examples=["Lahore", "Karachi", "Islamabad"])


class UserCityUpdateData(BaseSchema):
    selected_city: str
    is_lahore_express_eligible: bool


class TokenResponseData(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 86400
    user: Optional[UserPublic] = None
