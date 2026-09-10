"""
Bazaura.pk - Database Models Export
Ensures all SQLAlchemy 2.0 models are imported and registered with Base metadata.
"""

from app.models.base import Base, generate_prefixed_id
from app.models.user import User, ShippingAddress
from app.models.product import Category, Product, ProductVariant, ProductReview, Voucher
from app.models.order import Order, OrderItem, OrderTimeline
from app.models.request import CustomItemRequest, SourcingQuote
from app.models.content import EditorialContent, WishlistItem

__all__ = [
    "Base",
    "generate_prefixed_id",
    "User",
    "ShippingAddress",
    "Category",
    "Product",
    "ProductVariant",
    "ProductReview",
    "Voucher",
    "Order",
    "OrderItem",
    "OrderTimeline",
    "CustomItemRequest",
    "SourcingQuote",
    "EditorialContent",
    "WishlistItem",
]
