"""
Importing this package registers every model on `Base.metadata`
(required by Alembic autogenerate and by tests that create tables).
"""

from app.core.database import Base
from app.models.catalog import Category, Product, ProductReview, ProductVariant
from app.models.content import ContentBlock
from app.models.custom_request import CustomRequest, CustomRequestQuote
from app.models.order import Order, OrderItem, OrderStatusEvent
from app.models.user import Address, OtpCode, User
from app.models.voucher import Voucher
from app.models.wishlist import WishlistItem

__all__ = [
    "Base",
    "Address",
    "Category",
    "ContentBlock",
    "CustomRequest",
    "CustomRequestQuote",
    "Order",
    "OrderItem",
    "OrderStatusEvent",
    "OtpCode",
    "Product",
    "ProductReview",
    "ProductVariant",
    "User",
    "Voucher",
    "WishlistItem",
]
