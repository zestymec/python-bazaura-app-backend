"""
Allowed values for status/type columns.

Columns store these as plain strings (not native DB enums) so adding a value
later never needs a risky database migration.
"""

from enum import StrEnum


class UserRole(StrEnum):
    CUSTOMER = "customer"
    STAFF = "staff"  # handles orders and custom requests
    ADMIN = "admin"


class Gender(StrEnum):
    MEN = "MEN"
    WOMEN = "WOMEN"
    UNISEX = "UNISEX"
    KIDS = "KIDS"


class Season(StrEnum):
    SUMMER = "SUMMER"
    WINTER = "WINTER"
    ALL_SEASON = "ALL_SEASON"


class DeliveryType(StrEnum):
    STANDARD = "STANDARD"
    EXPRESS = "EXPRESS"  # same-city delivery within settings.EXPRESS_DELIVERY_HOURS


class DiscountType(StrEnum):
    PERCENT = "PERCENT"
    FLAT = "FLAT"


class OrderStatus(StrEnum):
    PLACED = "PLACED"
    CONFIRMED = "CONFIRMED"
    PACKED = "PACKED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RETURNED = "RETURNED"


class OrderSource(StrEnum):
    CATALOG = "CATALOG"
    CUSTOM_REQUEST = "CUSTOM_REQUEST"


class CustomRequestType(StrEnum):
    CUSTOM_ITEM = "CUSTOM_ITEM"  # "arrange this item for me"
    GIFT = "GIFT"  # "send this to someone else"


class CustomRequestStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    IN_REVIEW = "IN_REVIEW"
    QUOTED = "QUOTED"
    CONFIRMED = "CONFIRMED"  # customer accepted the quote; an order was created
    UNAVAILABLE = "UNAVAILABLE"
    CANCELLED = "CANCELLED"


class ContentType(StrEnum):
    BANNER = "BANNER"
    STORY = "STORY"


class ContentTargetType(StrEnum):
    CATEGORY = "CATEGORY"
    PRODUCT = "PRODUCT"
    COLLECTION = "COLLECTION"  # e.g. a search/filter preset such as season=WINTER
    CUSTOM_REQUEST = "CUSTOM_REQUEST"
    URL = "URL"
