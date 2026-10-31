"""
Delivery options, fees and customer-facing estimates.

The express window (currently 3 hours) and fees come from settings so they can
be changed through environment variables without a code change.
"""

from typing import List, Optional

from app.core.config import settings
from app.models.enums import DeliveryType
from app.schemas.cart import DeliveryOption


def delivery_label(delivery_type: DeliveryType) -> str:
    if delivery_type == DeliveryType.EXPRESS:
        return f"Express delivery ({settings.EXPRESS_DELIVERY_HOURS} hours)"
    return "Standard delivery"


def delivery_estimate(delivery_type: DeliveryType) -> str:
    if delivery_type == DeliveryType.EXPRESS:
        return f"Delivered within {settings.EXPRESS_DELIVERY_HOURS} hours"
    return f"Delivered in {settings.STANDARD_DELIVERY_ESTIMATE}"


def delivery_fee(delivery_type: DeliveryType, subtotal: int) -> int:
    if subtotal >= settings.FREE_SHIPPING_THRESHOLD_PKR:
        return 0
    if delivery_type == DeliveryType.EXPRESS:
        return settings.EXPRESS_DELIVERY_FEE_PKR
    return settings.STANDARD_DELIVERY_FEE_PKR


def delivery_options(subtotal: int, express_available: bool) -> List[DeliveryOption]:
    return [
        DeliveryOption(
            type=delivery_type,
            label=delivery_label(delivery_type),
            estimate=delivery_estimate(delivery_type),
            fee=delivery_fee(delivery_type, subtotal),
            available=delivery_type == DeliveryType.STANDARD or express_available,
        )
        for delivery_type in (DeliveryType.STANDARD, DeliveryType.EXPRESS)
    ]


def express_unavailable_reason(city: Optional[str], all_products_eligible: bool) -> Optional[str]:
    if not city:
        return "Select a delivery city to check express delivery"
    if not settings.is_express_city(city):
        cities = ", ".join(settings.EXPRESS_DELIVERY_CITIES)
        return f"Express delivery is currently available only in {cities}"
    if not all_products_eligible:
        return "Some items in your cart are not available for express delivery"
    return None
