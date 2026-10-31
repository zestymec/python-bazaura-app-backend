"""
Admin: categories, products and their size/colour variants.
"""

from typing import List, Optional

from fastapi import APIRouter, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminUser, DbSession, Pagination, StaffUser
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.catalog import Category, Product, ProductVariant
from app.schemas.admin import (
    AdminCategoryOut,
    AdminProductOut,
    AdminVariantOut,
    CategoryCreate,
    CategoryUpdate,
    ProductCreate,
    ProductUpdate,
    VariantCreate,
    VariantUpdate,
)
from app.schemas.common import ApiResponse, Page, PageMeta
from app.services import catalog_service
from app.utils.text import slugify

router = APIRouter()


async def _commit_or_conflict(db: AsyncSession, message: str) -> None:
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictError(message, code="DUPLICATE") from None


async def _ensure_category_exists(db: AsyncSession, category_id: Optional[str]) -> None:
    if category_id and await db.get(Category, category_id) is None:
        raise BadRequestError("Category does not exist", code="CATEGORY_NOT_FOUND")


async def _product_out(db: AsyncSession, product_id: str) -> AdminProductOut:
    product = await catalog_service.get_product_by_slug(db, product_id, include_inactive=True)
    return AdminProductOut.model_validate(product)


# --- Categories --------------------------------------------------------------
@router.get("/categories", response_model=ApiResponse[List[AdminCategoryOut]], tags=["Admin: catalog"])
async def list_categories(_: StaffUser, db: DbSession):
    rows = await db.execute(select(Category).order_by(Category.display_order, Category.name))
    return ApiResponse(data=[AdminCategoryOut.model_validate(c) for c in rows.scalars()])


@router.post(
    "/categories",
    response_model=ApiResponse[AdminCategoryOut],
    status_code=status.HTTP_201_CREATED,
    tags=["Admin: catalog"],
)
async def create_category(payload: CategoryCreate, _: AdminUser, db: DbSession):
    await _ensure_category_exists(db, payload.parent_id)
    data = payload.model_dump()
    data["slug"] = await catalog_service.unique_slug(db, Category, payload.slug or payload.name)
    category = Category(**data)
    db.add(category)
    await _commit_or_conflict(db, "A category with this slug already exists")
    return ApiResponse(message="Category created", data=AdminCategoryOut.model_validate(category))


@router.patch("/categories/{category_id}", response_model=ApiResponse[AdminCategoryOut], tags=["Admin: catalog"])
async def update_category(category_id: str, payload: CategoryUpdate, _: AdminUser, db: DbSession):
    category = await db.get(Category, category_id)
    if category is None:
        raise NotFoundError("Category not found")
    changes = payload.model_dump(exclude_unset=True)
    if "parent_id" in changes:
        if changes["parent_id"] == category_id:
            raise BadRequestError("A category cannot be its own parent")
        await _ensure_category_exists(db, changes["parent_id"])
    if changes.get("slug"):
        changes["slug"] = slugify(changes["slug"])
    for key, value in changes.items():
        setattr(category, key, value)
    await _commit_or_conflict(db, "A category with this slug already exists")
    return ApiResponse(message="Category updated", data=AdminCategoryOut.model_validate(category))


@router.delete("/categories/{category_id}", response_model=ApiResponse[None], tags=["Admin: catalog"])
async def delete_category(category_id: str, _: AdminUser, db: DbSession):
    category = await db.get(Category, category_id)
    if category is None:
        raise NotFoundError("Category not found")
    await db.delete(category)  # products and sub-categories are kept, their category becomes empty
    await db.commit()
    return ApiResponse(message="Category deleted")


# --- Products ----------------------------------------------------------------
@router.get("/products", response_model=ApiResponse[Page[AdminProductOut]], tags=["Admin: catalog"])
async def list_products(
    _: StaffUser,
    db: DbSession,
    pagination: Pagination,
    q: Optional[str] = Query(None, description="Search title, slug or SKU"),
    is_active: Optional[bool] = Query(None, alias="isActive"),
    low_stock: bool = Query(False, alias="lowStock", description="Products with any variant at 5 or fewer units"),
):
    query = select(Product)
    if q:
        term = f"%{q.lower()}%"
        sku_match = select(ProductVariant.id).where(
            ProductVariant.product_id == Product.id, func.lower(ProductVariant.sku).like(term)
        )
        query = query.where(or_(func.lower(Product.title).like(term), Product.slug.like(term), sku_match.exists()))
    if is_active is not None:
        query = query.where(Product.is_active.is_(is_active))
    if low_stock:
        query = query.where(
            select(ProductVariant.id)
            .where(
                ProductVariant.product_id == Product.id,
                ProductVariant.is_active.is_(True),
                ProductVariant.stock_quantity <= 5,
            )
            .exists()
        )
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = await db.execute(
        query.options(*catalog_service.PRODUCT_LOAD_OPTIONS)
        .order_by(Product.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    return ApiResponse(
        data=Page(
            items=[AdminProductOut.model_validate(p) for p in rows.scalars()],
            meta=PageMeta.build(pagination.page, pagination.limit, total),
        )
    )


@router.get("/products/{product_id}", response_model=ApiResponse[AdminProductOut], tags=["Admin: catalog"])
async def get_product(product_id: str, _: StaffUser, db: DbSession):
    return ApiResponse(data=await _product_out(db, product_id))


@router.post(
    "/products",
    response_model=ApiResponse[AdminProductOut],
    status_code=status.HTTP_201_CREATED,
    tags=["Admin: catalog"],
)
async def create_product(payload: ProductCreate, _: AdminUser, db: DbSession):
    await _ensure_category_exists(db, payload.category_id)
    data = payload.model_dump(exclude={"variants"})
    data["slug"] = await catalog_service.unique_slug(db, Product, payload.slug or payload.title)
    product = Product(**data, variants=[ProductVariant(**v.model_dump()) for v in payload.variants])
    db.add(product)
    await _commit_or_conflict(db, "Duplicate SKU or size/colour combination")
    return ApiResponse(message="Product created", data=await _product_out(db, product.id))


@router.patch("/products/{product_id}", response_model=ApiResponse[AdminProductOut], tags=["Admin: catalog"])
async def update_product(product_id: str, payload: ProductUpdate, _: AdminUser, db: DbSession):
    product = await db.get(Product, product_id)
    if product is None:
        raise NotFoundError("Product not found")
    changes = payload.model_dump(exclude_unset=True)
    if "category_id" in changes:
        await _ensure_category_exists(db, changes["category_id"])
    if changes.get("slug"):
        changes["slug"] = await catalog_service.unique_slug(db, Product, changes["slug"], exclude_id=product.id)
    for key, value in changes.items():
        setattr(product, key, value)
    await _commit_or_conflict(db, "A product with this slug already exists")
    return ApiResponse(message="Product updated", data=await _product_out(db, product.id))


@router.delete(
    "/products/{product_id}",
    response_model=ApiResponse[None],
    tags=["Admin: catalog"],
    summary="Archive a product (hidden from the store; order history is kept)",
)
async def archive_product(product_id: str, _: AdminUser, db: DbSession):
    product = await db.get(Product, product_id)
    if product is None:
        raise NotFoundError("Product not found")
    product.is_active = False
    await db.commit()
    return ApiResponse(message="Product archived")


# --- Variants ----------------------------------------------------------------
@router.post(
    "/products/{product_id}/variants",
    response_model=ApiResponse[AdminVariantOut],
    status_code=status.HTTP_201_CREATED,
    tags=["Admin: catalog"],
)
async def create_variant(product_id: str, payload: VariantCreate, _: AdminUser, db: DbSession):
    product = await db.get(Product, product_id)
    if product is None:
        raise NotFoundError("Product not found")
    variant = ProductVariant(product=product, **payload.model_dump())
    db.add(variant)
    await _commit_or_conflict(db, "Duplicate SKU or size/colour combination")
    return ApiResponse(message="Variant created", data=AdminVariantOut.model_validate(variant))


@router.patch("/variants/{variant_id}", response_model=ApiResponse[AdminVariantOut], tags=["Admin: catalog"])
async def update_variant(variant_id: str, payload: VariantUpdate, _: StaffUser, db: DbSession):
    """Staff may update stock; everything else is the same for admins."""
    variant = (
        await db.execute(
            select(ProductVariant)
            .options(catalog_service.selectinload(ProductVariant.product))
            .where(ProductVariant.id == variant_id)
        )
    ).scalar_one_or_none()
    if variant is None:
        raise NotFoundError("Variant not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(variant, key, value)
    await _commit_or_conflict(db, "Duplicate SKU or size/colour combination")
    return ApiResponse(message="Variant updated", data=AdminVariantOut.model_validate(variant))


@router.delete("/variants/{variant_id}", response_model=ApiResponse[None], tags=["Admin: catalog"])
async def delete_variant(variant_id: str, _: AdminUser, db: DbSession):
    variant = await db.get(ProductVariant, variant_id)
    if variant is None:
        raise NotFoundError("Variant not found")
    await db.delete(variant)
    await db.commit()
    return ApiResponse(message="Variant deleted")
