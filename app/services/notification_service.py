"""
Bazaura.pk - Notification Service (Demo Mode)
Provides mock wrappers for Firebase Cloud Messaging (FCM) push notifications and SMS alerts.
All methods log the intended payload and return a successful result without external calls.
"""

import logging
from typing import Dict, Any

from app.core.config import settings

logger = logging.getLogger("notification_service")
logger.setLevel(logging.INFO)


class NotificationService:
    """Demo notification service for local development.

    - ``send_push`` logs the message instead of contacting FCM.
    - ``send_sms`` logs the SMS payload; in production you would integrate with Twilio/Zong.
    """

    # ---------------------------------------------------------------------
    # Push notifications (FCM)
    # ---------------------------------------------------------------------
    def send_push(self, device_token: str, title: str, body: str, data: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Mock sending a push notification.
        Returns a dict mimicking the FCM response structure.
        """
        payload = {
            "to": device_token,
            "notification": {"title": title, "body": body},
            "data": data or {},
        }
        logger.info("Mock push notification sent: %s", payload)
        # Simulated successful response
        return {"success": 1, "failure": 0, "results": [{"message_id": "mock_msg_id"}]}

    # ---------------------------------------------------------------------
    # SMS alerts
    # ---------------------------------------------------------------------
    def send_sms(self, phone: str, message: str) -> Dict[str, Any]:
        """Mock sending an SMS using the configured gateway.
        Returns a dict indicating success.
        """
        payload = {"to": phone, "message": message, "sender_id": settings.SMS_SENDER_ID}
        logger.info("Mock SMS sent: %s", payload)
        return {"status": "sent", "message_id": f"sms_{phone}_{int(__import__('time').time())}"}


__all__ = ["NotificationService"]
