"""
Token handling, OTP hashing and Pakistani phone number normalisation.

FastAPI auth dependencies (current user, role checks) live in `app/api/deps.py`.
"""

import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, Optional

import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def normalize_pakistan_phone(phone: str) -> str:
    """
    Converts any common Pakistani mobile format to E.164 (`+923001234567`).
    Raises ValueError for anything that is not a valid PK mobile number.
    """
    cleaned = re.sub(r"[\s\-\(\)]", "", phone.strip())
    if cleaned.startswith("+92"):
        normalized = cleaned
    elif cleaned.startswith("0092"):
        normalized = f"+{cleaned[2:]}"
    elif cleaned.startswith("92") and len(cleaned) == 12:
        normalized = f"+{cleaned}"
    elif cleaned.startswith("0") and len(cleaned) == 11:
        normalized = f"+92{cleaned[1:]}"
    elif cleaned.startswith("3") and len(cleaned) == 10:
        normalized = f"+92{cleaned}"
    else:
        normalized = cleaned

    if not re.fullmatch(r"\+923\d{9}", normalized):
        raise ValueError("Invalid Pakistani mobile number. Expected format: 03001234567")
    return normalized


def generate_otp() -> str:
    if settings.OTP_FIXED_CODE:
        return settings.OTP_FIXED_CODE
    return "".join(secrets.choice("0123456789") for _ in range(settings.OTP_LENGTH))


def hash_otp(phone: str, code: str) -> str:
    """OTPs are stored as keyed hashes so a database leak does not expose live codes."""
    message = f"{phone}:{code}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def otp_matches(phone: str, code: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(phone, code), code_hash)


def _create_token(
    subject: str, token_type: str, expires_delta: timedelta, claims: Optional[Dict[str, Any]] = None
) -> str:
    now = datetime.now(UTC)
    payload: Dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": secrets.token_hex(8),
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str, role: str) -> str:
    return _create_token(
        subject,
        ACCESS_TOKEN_TYPE,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        {"role": role},
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(subject, REFRESH_TOKEN_TYPE, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str, expected_type: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired", code="TOKEN_EXPIRED") from None
    except jwt.InvalidTokenError:
        raise UnauthorizedError("Invalid authentication token", code="TOKEN_INVALID") from None

    if payload.get("type") != expected_type or not payload.get("sub"):
        raise UnauthorizedError("Invalid authentication token", code="TOKEN_INVALID")
    return payload
