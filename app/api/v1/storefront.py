"""
Storefront-wide endpoints: home feed, runtime config, SEO sitemap and uploads.
"""

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.models.catalog import Category, Product
from app.models.content import ContentBlock
from app.models.enums import ContentType
from app.schemas.catalog import CategoryOut, ProductCard
from app.schemas.common import ApiResponse
from app.schemas.storefront import (
    ContentBlockOut,
    HomeFeed,
    PresignedUpload,
    PresignedUploadRequest,
    Sitemap,
    SitemapEntry,
    StorefrontConfig,
)
from app.services import catalog_service, delivery, storage_service
from app.services.catalog_service import ProductSort

router = APIRouter(tags=["Storefront"])

HOME_RAIL_SIZE = 12


@router.get(
    "/storefront/config", response_model=ApiResponse[StorefrontConfig], summary="Business settings for the apps"
)
async def get_config():
    return ApiResponse(
        data=StorefrontConfig(
            free_shipping_threshold=settings.FREE_SHIPPING_THRESHOLD_PKR,
            express_delivery_hours=settings.EXPRESS_DELIVERY_HOURS,
            express_delivery_cities=settings.EXPRESS_DELIVERY_CITIES,
            delivery_options=delivery.delivery_options(subtotal=0, express_available=True),
            gift_wrap_fee=settings.GIFT_WRAP_FEE_PKR,
        )
    )


@router.get(
    "/storefront/home", response_model=ApiResponse[HomeFeed], summary="Everything the home screen needs in one call"
)
async def get_home(db: DbSession):
    blocks = [
        b for b in (await db.execute(select(ContentBlock).order_by(ContentBlock.display_order))).scalars() if b.is_live
    ]
    featured_categories = (
        await db.execute(
            select(Category)
            .where(Category.is_active.is_(True), Category.is_featured.is_(True))
            .order_by(Category.display_order)
        )
    ).scalars()

    async def rail(**filters):
        products, _ = await catalog_service.list_products(db, in_stock_only=True, limit=HOME_RAIL_SIZE, **filters)
        return [ProductCard.model_validate(p) for p in products]

    return ApiResponse(
        data=HomeFeed(
            banners=[ContentBlockOut.model_validate(b) for b in blocks if b.content_type == ContentType.BANNER],
            stories=[ContentBlockOut.model_validate(b) for b in blocks if b.content_type == ContentType.STORY],
            featured_categories=[CategoryOut.model_validate(c) for c in featured_categories],
            new_arrivals=await rail(sort=ProductSort.NEWEST),
            bestsellers=await rail(sort=ProductSort.POPULAR),
            on_sale=await rail(on_sale_only=True, sort=ProductSort.POPULAR),
        )
    )


@router.get(
    "/seo/sitemap",
    response_model=ApiResponse[Sitemap],
    summary="All public product and category URLs (for Next.js sitemap.xml)",
)
async def get_sitemap(db: DbSession):
    products = await db.execute(select(Product.slug, Product.updated_at).where(Product.is_active.is_(True)))
    categories = await db.execute(select(Category.slug, Category.updated_at).where(Category.is_active.is_(True)))
    return ApiResponse(
        data=Sitemap(
            base_url=settings.SITE_URL,
            products=[SitemapEntry(path=f"/product/{slug}", updated_at=updated) for slug, updated in products],
            categories=[SitemapEntry(path=f"/category/{slug}", updated_at=updated) for slug, updated in categories],
        )
    )


@router.post(
    "/uploads/presigned-url", response_model=ApiResponse[PresignedUpload], summary="Get a URL to upload an image"
)
async def create_upload_url(payload: PresignedUploadRequest, user: CurrentUser):
    upload = storage_service.create_presigned_upload(
        payload.folder, payload.file_name, payload.content_type, is_staff=user.is_staff
    )
    return ApiResponse(data=upload)
