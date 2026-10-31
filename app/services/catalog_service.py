"""
Catalog queries: product search/filtering, category trees and slug helpers.
"""

from enum import StrEnum
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy import Select, String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.catalog import Category, Product, ProductVariant
from app.models.enums import Gender, Season
from app.utils.text import slugify


class ProductSort(StrEnum):
    NEWEST = "newest"
    POPULAR = "popular"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    RATING = "rating"


PRODUCT_LOAD_OPTIONS = (selectinload(Product.variants), selectinload(Product.category))


async def list_products(
    db: AsyncSession,
    *,
    category_slug: Optional[str] = None,
    gender: Optional[Gender] = None,
    season: Optional[Season] = None,
    sizes: Sequence[str] = (),
    colors: Sequence[str] = (),
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    search: Optional[str] = None,
    express_only: bool = False,
    in_stock_only: bool = False,
    featured_only: bool = False,
    on_sale_only: bool = False,
    sort: ProductSort = ProductSort.NEWEST,
    offset: int = 0,
    limit: int = 20,
) -> Tuple[List[Product], int]:
    query: Select = select(Product).where(Product.is_active.is_(True))

    if category_slug:
        category_ids = await category_ids_with_descendants(db, category_slug)
        query = query.where(Product.category_id.in_(category_ids))
    if gender:
        query = query.where(Product.gender.in_([gender, Gender.UNISEX]))
    if season:
        query = query.where(Product.season == season)
    if min_price is not None:
        query = query.where(Product.price >= min_price)
    if max_price is not None:
        query = query.where(Product.price <= max_price)
    if express_only:
        query = query.where(Product.is_express_eligible.is_(True))
    if featured_only:
        query = query.where(Product.is_featured.is_(True))
    if on_sale_only:
        query = query.where(Product.compare_at_price > Product.price)
    if search:
        term = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Product.title).like(term),
                func.lower(Product.brand).like(term),
                func.lower(Product.fabric).like(term),
                func.lower(cast(Product.tags, String)).like(term),
            )
        )

    variant_filters = [ProductVariant.product_id == Product.id, ProductVariant.is_active.is_(True)]
    if sizes:
        variant_filters.append(ProductVariant.size.in_(sizes))
    if colors:
        variant_filters.append(func.lower(ProductVariant.color).in_([c.lower() for c in colors]))
    if in_stock_only or sizes or colors:
        variant_filters.append(ProductVariant.stock_quantity > 0)
        query = query.where(select(ProductVariant.id).where(*variant_filters).exists())

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

    order_by = {
        ProductSort.NEWEST: (Product.created_at.desc(),),
        ProductSort.POPULAR: (Product.sold_count.desc(), Product.created_at.desc()),
        ProductSort.PRICE_ASC: (Product.price.asc(),),
        ProductSort.PRICE_DESC: (Product.price.desc(),),
        ProductSort.RATING: (Product.rating_avg.desc(), Product.review_count.desc()),
    }[sort]
    rows = await db.execute(
        query.options(*PRODUCT_LOAD_OPTIONS).order_by(*order_by, Product.id).offset(offset).limit(limit)
    )
    return list(rows.scalars().all()), total


async def get_product_by_slug(db: AsyncSession, slug_or_id: str, *, include_inactive: bool = False) -> Product:
    query = (
        select(Product).options(*PRODUCT_LOAD_OPTIONS).where(or_(Product.slug == slug_or_id, Product.id == slug_or_id))
    )
    if not include_inactive:
        query = query.where(Product.is_active.is_(True))
    product = (await db.execute(query)).scalar_one_or_none()
    if product is None:
        raise NotFoundError("Product not found", code="PRODUCT_NOT_FOUND")
    return product


async def related_products(db: AsyncSession, product: Product, limit: int = 8) -> List[Product]:
    query = (
        select(Product)
        .options(*PRODUCT_LOAD_OPTIONS)
        .where(Product.is_active.is_(True), Product.id != product.id)
        .order_by(Product.sold_count.desc(), Product.created_at.desc())
        .limit(limit)
    )
    if product.category_id:
        query = query.where(Product.category_id == product.category_id)
    return list((await db.execute(query)).scalars().all())


# --- Categories --------------------------------------------------------------
async def _active_categories(db: AsyncSession) -> List[Category]:
    rows = await db.execute(
        select(Category).where(Category.is_active.is_(True)).order_by(Category.display_order, Category.name)
    )
    return list(rows.scalars().all())


async def category_tree(db: AsyncSession) -> List[dict]:
    from app.schemas.catalog import CategoryOut  # local import avoids a schemas<->services cycle

    categories = await _active_categories(db)
    nodes: Dict[str, dict] = {c.id: {**CategoryOut.model_validate(c).model_dump(), "children": []} for c in categories}
    roots: List[dict] = []
    for category in categories:
        node = nodes[category.id]
        if category.parent_id and category.parent_id in nodes:
            nodes[category.parent_id]["children"].append(node)
        else:
            roots.append(node)
    return roots


async def get_category_by_slug(db: AsyncSession, slug: str) -> Tuple[Category, List[Category], List[Category]]:
    """Returns (category, ancestors from root, direct children)."""
    categories = await _active_categories(db)
    by_id = {c.id: c for c in categories}
    category = next((c for c in categories if c.slug == slug), None)
    if category is None:
        raise NotFoundError("Category not found", code="CATEGORY_NOT_FOUND")

    ancestors: List[Category] = []
    parent_id = category.parent_id
    while parent_id and parent_id in by_id and len(ancestors) < 10:
        ancestors.insert(0, by_id[parent_id])
        parent_id = by_id[parent_id].parent_id
    children = [c for c in categories if c.parent_id == category.id]
    return category, ancestors, children


async def category_path(db: AsyncSession, category_id: Optional[str]) -> List[Category]:
    if not category_id:
        return []
    category = await db.get(Category, category_id)
    if category is None:
        return []
    if not category.is_active:
        return [category]
    _, ancestors, _ = await get_category_by_slug(db, category.slug)
    return [*ancestors, category]


async def category_ids_with_descendants(db: AsyncSession, slug: str) -> List[str]:
    categories = await _active_categories(db)
    root = next((c for c in categories if c.slug == slug), None)
    if root is None:
        raise NotFoundError("Category not found", code="CATEGORY_NOT_FOUND")
    ids, frontier = [root.id], [root.id]
    while frontier:
        frontier = [c.id for c in categories if c.parent_id in frontier]
        ids.extend(frontier)
    return ids


# --- Slugs -------------------------------------------------------------------
async def unique_slug(db: AsyncSession, model, source: str, *, exclude_id: Optional[str] = None) -> str:
    base = slugify(source)
    candidate, suffix = base, 2
    while True:
        query = select(model.id).where(model.slug == candidate)
        if exclude_id:
            query = query.where(model.id != exclude_id)
        if (await db.execute(query)).first() is None:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1
