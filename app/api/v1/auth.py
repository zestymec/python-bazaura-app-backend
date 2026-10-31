from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.auth import AuthResult, OtpRequest, OtpRequestResult, OtpVerify, RefreshRequest, TokenPair
from app.schemas.common import ApiResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/otp/request", response_model=ApiResponse[OtpRequestResult], summary="Send a login code by SMS")
async def request_otp(payload: OtpRequest, db: DbSession):
    result = await auth_service.request_otp(db, payload.phone)
    return ApiResponse(message="Code sent", data=result)


@router.post("/otp/verify", response_model=ApiResponse[AuthResult], summary="Verify code and log in / sign up")
async def verify_otp(payload: OtpVerify, db: DbSession):
    result = await auth_service.verify_otp(db, payload.phone, payload.code, payload.full_name)
    return ApiResponse(message="Logged in", data=result)


@router.post("/refresh", response_model=ApiResponse[TokenPair], summary="Exchange a refresh token for new tokens")
async def refresh(payload: RefreshRequest, db: DbSession):
    return ApiResponse(data=await auth_service.refresh_tokens(db, payload.refresh_token))
