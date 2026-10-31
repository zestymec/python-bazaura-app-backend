"""
Outbound SMS. The `console` provider only logs messages, which is what
development and tests use. Plug a real Pakistani SMS gateway in `_send_via_provider`.
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_sms(phone: str, message: str) -> None:
    if settings.SMS_PROVIDER == "console":
        logger.info("SMS to %s: %s", phone, message)
        return
    await _send_via_provider(phone, message)


async def _send_via_provider(phone: str, message: str) -> None:
    raise NotImplementedError(f"SMS provider '{settings.SMS_PROVIDER}' is not configured yet")
