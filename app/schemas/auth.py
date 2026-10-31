from typing import Optional

from pydantic import Field

from app.schemas.common import BaseSchema
from app.schemas.user import UserOut
from app.schemas.validators import PakistanPhone


class OtpRequest(BaseSchema):
    phone: PakistanPhone = Field(..., examples=["03001234567"])


class OtpRequestResult(BaseSchema):
    expires_in_seconds: int
    resend_available_in_seconds: int


class OtpVerify(BaseSchema):
    phone: PakistanPhone = Field(..., examples=["03001234567"])
    code: str = Field(..., min_length=4, max_length=8, examples=["123456"])
    full_name: Optional[str] = Field(None, max_length=128, description="Used only when creating a new account")


class RefreshRequest(BaseSchema):
    refresh_token: str


class TokenPair(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthResult(TokenPair):
    user: UserOut
    is_new_user: bool
