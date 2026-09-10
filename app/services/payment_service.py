"""
Bazaura.pk - Payment Service (Demo Mode)
Provides mock implementations for JazzCash, EasyPaisa, and related webhook handling.
All methods return static, well‑formed responses suitable for local testing.
"""

from datetime import datetime, timedelta
from typing import Dict, Any

from app.core.config import settings


class PaymentService:
    """Demo payment gateway service.

    In production this class would integrate with real JazzCash/EasyPaisa SDKs.
    The demo versions simply echo the request data and generate deterministic IDs.
    """

    # ---------------------------------------------------------------------
    # JazzCash
    # ---------------------------------------------------------------------
    def initiate_jazzcash(self, amount: int, order_id: str, customer_phone: str) -> Dict[str, Any]:
        """Return a mock response for JazzCash payment initiation.

        Parameters
        ----------
        amount: int
            Amount in PKR.
        order_id: str
            Bazaura order identifier.
        customer_phone: str
            Normalised phone number.
        """
        return {
            "status": "SUCCESS",
            "txn_ref": f"JC-{order_id}",
            "amount": amount,
            "currency": "PKR",
            "message": "JazzCash payment simulated",
            "payment_url": f"https://demo.jazzcash.com/pay?ref=JC-{order_id}&amount={amount}",
        }

    def verify_jazzcash_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a JazzCash webhook payload (demo – always succeeds)."""
        # In real life you would verify HMAC signature using settings.JAZZCASH_HASH_SECRET
        return {
            "order_id": payload.get("order_id", "unknown"),
            "status": payload.get("status", "SUCCESS"),
            "amount": payload.get("amount", 0),
            "verified": True,
        }

    # ---------------------------------------------------------------------
    # EasyPaisa
    # ---------------------------------------------------------------------
    def initiate_easypaisa(self, amount: int, order_id: str, customer_phone: str) -> Dict[str, Any]:
        """Return a mock EasyPaisa payment initiation response."""
        return {
            "status": "SUCCESS",
            "txn_ref": f"EP-{order_id}",
            "amount": amount,
            "currency": "PKR",
            "message": "EasyPaisa payment simulated",
            "payment_url": f"https://demo.easypaisa.com/pay?ref=EP-{order_id}&amount={amount}",
        }

    def verify_easypaisa_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate an EasyPaisa webhook payload (demo – always succeeds)."""
        return {
            "order_id": payload.get("order_id", "unknown"),
            "status": payload.get("status", "SUCCESS"),
            "amount": payload.get("amount", 0),
            "verified": True,
        }


__all__ = ["PaymentService"]
