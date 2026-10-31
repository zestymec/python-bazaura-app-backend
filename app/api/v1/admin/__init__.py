"""
Staff/admin endpoints, all under /api/v1/admin. These power the future dashboard.
`staff` can manage orders, custom requests and stock; `admin` can do everything.
"""

from fastapi import APIRouter

from app.api.v1.admin import catalog, marketing, orders, users

router = APIRouter(prefix="/admin")
for module in (catalog, orders, marketing, users):
    router.include_router(module.router)
