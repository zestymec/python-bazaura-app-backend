"""
Public catalog: categories, product listing/search, product detail and reviews.
"""

from typing import List, Optional

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession, Pagination
from app.core.exceptions import ConflictError
from app.models.catalog import ProductReview
from app.models.enums import Gender, OrderStatus, Season
from app.models.order import Order, OrderItem
from app.schemas.catalog import CategoryDetail, CategoryNode, ProductCard, ProductDetail, ReviewCreate, ReviewOut
from app.schemas.common import ApiResponse, Page, PageMeta
from app.services import catalog_service
from app.services.catalog_service import ProductSort

router = APIRouter(tags=["Catalog"])


@router.get("/categories", response_model=ApiResponse[List[CategoryNode]], summary="Category tree")
async def list_categories(db: DbSession):
    return ApiResponse(data=await catalog_service.category_tree(db))


@router.get("/categories/{slug}", response_model=ApiResponse[CategoryDetail], summary="Category page data (with SEO)")
async def get_category(slug: str, db: DbSession):
    category, ancestors, children = await catalog_service.get_category_by_slug(db, slug)
    return ApiResponse(data=CategoryDetail.from_category(category, ancestors, children))


@router.get(
    "/products", response_model=ApiResponse[Page[ProductCard]], summary="List, filter, search and sort products"
)
async def list_products(
    db: DbSession,
    pagination: Pagination,
    category: Optional[str] = Query(None, description="Category slug; includes sub-categories"),
    gender: Optional[Gender] = None,
    season: Optional[Season] = None,
    size: List[str] = Query([], description="Repeatable: ?size=M&size=L"),
    color: List[str] = Query([], description="Repeatable: ?color=Black"),
    min_price: Optional[int] = Query(None, ge=0, alias="minPrice"),
    max_price: Optional[int] = Query(None, ge=0, alias="maxPrice"),
    q: Optional[str] = Query(None, min_length=2, max_length=100, description="Search text"),
    express: bool = Query(False, description="Only express-eligible products"),
    in_stock: bool = Query(False, alias="inStock"),
    on_sale: bool = Query(False, alias="onSale"),
    featured: bool = False,
    sort: ProductSort = ProductSort.NEWEST,
):
    products, total = await catalog_service.list_products(
        db,
        category_slug=category,
        gender=gender,
        season=season,
        sizes=size,
        colors=color,
        min_price=min_price,
        max_price=max_price,
        search=q,
        express_only=express,
        in_stock_only=in_stock,
        on_sale_only=on_sale,
        featured_only=featured,
        sort=sort,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return ApiResponse(
        data=Page(
            items=[ProductCard.model_validate(p) for p in products],
            meta=PageMeta.build(pagination.page, pagination.limit, total),
        )
    )


@router.get("/products/{slug}", response_model=ApiResponse[ProductDetail], summary="Product page data (by slug or id)")
async def get_product(slug: str, db: DbSession):
    product = await catalog_service.get_product_by_slug(db, slug)
    path = await catalog_service.category_path(db, product.category_id)
    return ApiResponse(data=ProductDetail.from_product(product, path))


@router.get("/products/{slug}/related", response_model=ApiResponse[List[ProductCard]], summary="Related products")
async def get_related_products(slug: str, db: DbSession, limit: int = Query(8, ge=1, le=20)):
    product = await catalog_service.get_product_by_slug(db, slug)
    related = await catalog_service.related_products(db, product, limit)
    return ApiResponse(data=[ProductCard.model_validate(p) for p in related])


@router.get("/products/{slug}/reviews", response_model=ApiResponse[Page[ReviewOut]], summary="Published reviews")
async def list_reviews(slug: str, db: DbSession, pagination: Pagination):
    product = await catalog_service.get_product_by_slug(db, slug)
    base = select(ProductReview).where(ProductReview.product_id == product.id, ProductReview.is_published.is_(True))
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = await db.execute(
        base.order_by(ProductReview.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    )
    return ApiResponse(
        data=Page(
            items=[ReviewOut.model_validate(r) for r in rows.scalars()],
            meta=PageMeta.build(pagination.page, pagination.limit, total),
        )
    )


@router.post(
    "/products/{slug}/reviews",
    response_model=ApiResponse[ReviewOut],
    status_code=status.HTTP_201_CREATED,
    summary="Write a review (one per customer per product)",
)
async def create_review(slug: str, payload: ReviewCreate, user: CurrentUser, db: DbSession):
    product = await catalog_service.get_product_by_slug(db, slug)
    purchased = (
        await db.execute(
            select(OrderItem.id)
            .join(Order)
            .where(Order.user_id == user.id, Order.status == OrderStatus.DELIVERED, OrderItem.product_id == product.id)
            .limit(1)
        )
    ).first() is not None

    review = ProductReview(
        product_id=product.id,
        user_id=user.id,
        author_name=user.full_name or "Bazaura customer",
        is_verified_purchase=purchased,
        **payload.model_dump(),
    )
    db.add(review)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise ConflictError("You have already reviewed this product", code="REVIEW_EXISTS") from None

    stats = (
        await db.execute(
            select(func.avg(ProductReview.rating), func.count()).where(
                ProductReview.product_id == product.id, ProductReview.is_published.is_(True)
            )
        )
    ).one()
    product.rating_avg = round(float(stats[0] or 0), 2)
    product.review_count = stats[1]
    await db.commit()
    return ApiResponse(message="Thanks for your review", data=ReviewOut.model_validate(review))
