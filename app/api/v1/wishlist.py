from typing import List

from fastapi import APIRouter
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.catalog import Product
from app.models.wishlist import WishlistItem
from app.schemas.catalog import ProductCard
from app.schemas.common import ApiResponse
from app.services import catalog_service

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


@router.get("", response_model=ApiResponse[List[ProductCard]], summary="My wishlist (newest first)")
async def get_wishlist(user: CurrentUser, db: DbSession):
    rows = await db.execute(
        select(WishlistItem)
        .options(selectinload(WishlistItem.product).options(*catalog_service.PRODUCT_LOAD_OPTIONS))
        .join(Product)
        .where(WishlistItem.user_id == user.id, Product.is_active.is_(True))
        .order_by(WishlistItem.created_at.desc())
    )
    return ApiResponse(data=[ProductCard.model_validate(item.product) for item in rows.scalars()])


@router.put("/{product_id}", response_model=ApiResponse[None], summary="Add a product (idempotent)")
async def add_to_wishlist(product_id: str, user: CurrentUser, db: DbSession):
    product = await catalog_service.get_product_by_slug(db, product_id)
    exists = (
        await db.execute(
            select(WishlistItem.id).where(WishlistItem.user_id == user.id, WishlistItem.product_id == product.id)
        )
    ).first()
    if not exists:
        db.add(WishlistItem(user_id=user.id, product_id=product.id))
        await db.commit()
    return ApiResponse(message="Added to wishlist")


@router.delete("/{product_id}", response_model=ApiResponse[None], summary="Remove a product (idempotent)")
async def remove_from_wishlist(product_id: str, user: CurrentUser, db: DbSession):
    await db.execute(delete(WishlistItem).where(WishlistItem.user_id == user.id, WishlistItem.product_id == product_id))
    await db.commit()
    return ApiResponse(message="Removed from wishlist")
