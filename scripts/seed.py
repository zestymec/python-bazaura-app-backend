"""
Loads sample categories, products, a voucher and a banner so the apps have
something to show during development. Safe to run more than once.

    python -m scripts.seed
"""

import asyncio
import itertools

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import Category, ContentBlock, Product, ProductVariant, Voucher
from app.models.enums import ContentTargetType, ContentType, DiscountType, Gender, Season
from app.utils.text import slugify

PLACEHOLDER = "https://placehold.co/800x1000/111/fff?text="

CATEGORIES = {
    "Hoodies": "Hoodies & sweatshirts for winter",
    "Jackets": "Puffer, bomber and denim jackets",
    "Shirts": "Casual and formal shirts",
    "T-Shirts": "Everyday cotton tees",
    "Trousers": "Chinos, cargos and dress pants",
    "Tracksuits": "Matching tracksuit sets",
}

# (title, category, price, compare_at, season, fabric, colors, sizes)
PRODUCTS = [
    (
        "Classic Pullover Hoodie",
        "Hoodies",
        3499,
        4499,
        Season.WINTER,
        "Fleece",
        ["Black", "Grey"],
        ["S", "M", "L", "XL"],
    ),
    ("Oversized Zip Hoodie", "Hoodies", 3999, None, Season.WINTER, "Cotton Fleece", ["Olive"], ["M", "L", "XL"]),
    ("Puffer Jacket", "Jackets", 8999, 10999, Season.WINTER, "Nylon", ["Black", "Navy"], ["M", "L", "XL"]),
    ("Denim Trucker Jacket", "Jackets", 6499, None, Season.ALL_SEASON, "Denim", ["Blue"], ["S", "M", "L"]),
    (
        "Oxford Button-Down Shirt",
        "Shirts",
        2999,
        None,
        Season.ALL_SEASON,
        "Cotton",
        ["White", "Sky Blue"],
        ["S", "M", "L", "XL"],
    ),
    ("Linen Summer Shirt", "Shirts", 3299, 3999, Season.SUMMER, "Linen", ["Beige"], ["M", "L", "XL"]),
    (
        "Essential Crew Neck Tee",
        "T-Shirts",
        1299,
        None,
        Season.SUMMER,
        "Cotton",
        ["Black", "White"],
        ["S", "M", "L", "XL"],
    ),
    (
        "Slim Fit Chino Trouser",
        "Trousers",
        3499,
        None,
        Season.ALL_SEASON,
        "Cotton Twill",
        ["Khaki", "Navy"],
        ["30", "32", "34", "36"],
    ),
    ("Cargo Pants", "Trousers", 3799, 4299, Season.ALL_SEASON, "Cotton", ["Black"], ["30", "32", "34"]),
    ("Fleece Tracksuit Set", "Tracksuits", 6999, 8499, Season.WINTER, "Fleece", ["Charcoal"], ["M", "L", "XL"]),
]


async def seed() -> None:
    async with SessionLocal() as db:
        if (await db.execute(select(Category.id).limit(1))).first():
            print("Database already has data — skipping seed.")
            return

        men = Category(name="Men", slug="men", is_featured=True, display_order=0, description="Men's clothing")
        children = {
            name: Category(name=name, slug=f"men-{slugify(name)}", parent=men, description=desc, display_order=i)
            for i, (name, desc) in enumerate(CATEGORIES.items())
        }
        db.add(men)

        for index, (title, category, price, compare_at, season, fabric, colors, sizes) in enumerate(PRODUCTS):
            sku_base = "".join(word[0] for word in title.split()).upper()
            product = Product(
                title=title,
                slug=slugify(title),
                category=children[category],
                price=price,
                compare_at_price=compare_at,
                gender=Gender.MEN,
                season=season,
                fabric=fabric,
                fit="Regular",
                short_description=f"{fabric} {category.lower().rstrip('s')} by Bazaura.",
                description=f"{title} made from premium {fabric.lower()}. Designed in Pakistan for everyday comfort.",
                images=[f"{PLACEHOLDER}{slugify(title)}"],
                tags=[category.lower(), season.lower(), fabric.lower()],
                badge="SALE" if compare_at else ("NEW" if index < 3 else None),
                is_featured=index % 3 == 0,
                variants=[
                    ProductVariant(
                        sku=f"{sku_base}-{color[:3].upper()}-{size}",
                        size=size,
                        color=color,
                        stock_quantity=10,
                        display_order=order,
                    )
                    for order, (color, size) in enumerate(itertools.product(colors, sizes))
                ],
            )
            db.add(product)

        db.add(
            Voucher(
                code="WELCOME10",
                description="10% off your first order (up to Rs. 1,000)",
                discount_type=DiscountType.PERCENT,
                value=10,
                max_discount=1000,
                min_order_amount=2000,
            )
        )
        db.add(
            ContentBlock(
                content_type=ContentType.BANNER,
                title="Winter Collection",
                subtitle="Hoodies, jackets and tracksuits",
                image_url=f"{PLACEHOLDER}winter-collection",
                cta_text="Shop now",
                target_type=ContentTargetType.COLLECTION,
                target_value="season=WINTER",
            )
        )
        await db.commit()
        print(f"Seeded {len(CATEGORIES) + 1} categories, {len(PRODUCTS)} products, 1 voucher and 1 banner.")


if __name__ == "__main__":
    asyncio.run(seed())
