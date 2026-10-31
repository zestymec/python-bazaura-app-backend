"""
Version 1 of the public API. Every router is mounted under /api/v1.
"""

from fastapi import APIRouter

from app.api.v1 import admin, auth, cart, catalog, custom_requests, orders, storefront, users, wishlist

api_router = APIRouter()
for module in (auth, users, catalog, cart, orders, custom_requests, wishlist, storefront, admin):
    api_router.include_router(module.router)
