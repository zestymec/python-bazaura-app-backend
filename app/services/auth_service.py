"""
Phone + OTP login.

Flow: request_otp() stores a hashed code and SMSes it -> verify_otp() checks it,
creates the account on first login, and returns access + refresh tokens.
"""

from datetime import timedelta
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestError, ForbiddenError, TooManyRequestsError
from app.core.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_otp,
    hash_otp,
    otp_matches,
)
from app.models.base import utcnow
from app.models.user import OtpCode, User
from app.schemas.auth import AuthResult, OtpRequestResult, TokenPair
from app.schemas.user import UserOut
from app.services import notification_service


async def request_otp(db: AsyncSession, phone: str) -> OtpRequestResult:
    now = utcnow()
    window_start = now - timedelta(minutes=settings.OTP_REQUEST_WINDOW_MINUTES)

    recent = (
        await db.execute(
            select(func.count(), func.max(OtpCode.created_at)).where(
                OtpCode.phone == phone, OtpCode.created_at >= window_start
            )
        )
    ).one()
    recent_count, last_sent_at = recent

    if last_sent_at and (now - last_sent_at).total_seconds() < settings.OTP_RESEND_COOLDOWN_SECONDS:
        wait = settings.OTP_RESEND_COOLDOWN_SECONDS - int((now - last_sent_at).total_seconds())
        raise TooManyRequestsError(f"Please wait {wait} seconds before requesting a new code", code="OTP_COOLDOWN")
    if recent_count >= settings.OTP_MAX_REQUESTS_PER_WINDOW:
        raise TooManyRequestsError("Too many codes requested. Please try again later", code="OTP_RATE_LIMITED")

    # Only the newest code is valid.
    await db.execute(
        update(OtpCode).where(OtpCode.phone == phone, OtpCode.consumed_at.is_(None)).values(consumed_at=now)
    )
    code = generate_otp()
    db.add(
        OtpCode(
            phone=phone,
            code_hash=hash_otp(phone, code),
            expires_at=now + timedelta(seconds=settings.OTP_EXPIRY_SECONDS),
        )
    )
    await db.commit()

    await notification_service.send_sms(phone, f"Your Bazaura.pk login code is {code}. Do not share it with anyone.")
    return OtpRequestResult(
        expires_in_seconds=settings.OTP_EXPIRY_SECONDS,
        resend_available_in_seconds=settings.OTP_RESEND_COOLDOWN_SECONDS,
    )


async def verify_otp(db: AsyncSession, phone: str, code: str, full_name: Optional[str]) -> AuthResult:
    now = utcnow()
    otp = (
        await db.execute(
            select(OtpCode)
            .where(OtpCode.phone == phone, OtpCode.consumed_at.is_(None))
            .order_by(OtpCode.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if otp is None or otp.expires_at < now:
        raise BadRequestError("Code expired. Please request a new one", code="OTP_EXPIRED")
    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise TooManyRequestsError("Too many wrong attempts. Please request a new code", code="OTP_LOCKED")
    if not otp_matches(phone, code, otp.code_hash):
        otp.attempts += 1
        await db.commit()
        raise BadRequestError("Incorrect code", code="OTP_INVALID")

    otp.consumed_at = now
    user = (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
    is_new_user = user is None
    if is_new_user:
        user = User(phone=phone, full_name=(full_name or "").strip() or None)
        db.add(user)
    elif not user.is_active:
        await db.commit()
        raise ForbiddenError("This account has been deactivated", code="ACCOUNT_INACTIVE")

    user.last_login_at = now
    await db.commit()
    await db.refresh(user)

    tokens = issue_tokens(user)
    return AuthResult(**tokens.model_dump(), user=UserOut.model_validate(user), is_new_user=is_new_user)


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenPair:
    payload = decode_token(refresh_token, REFRESH_TOKEN_TYPE)
    user = await db.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise ForbiddenError("This account is not available", code="ACCOUNT_INACTIVE")
    return issue_tokens(user)


def issue_tokens(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
