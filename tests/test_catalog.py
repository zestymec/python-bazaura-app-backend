async def test_category_tree_and_detail(client, catalog):
    tree = (await client.get("/api/v1/categories")).json()["data"]
    assert tree[0]["slug"] == "men"
    assert tree[0]["children"][0]["slug"] == "men-hoodies"

    detail = (await client.get("/api/v1/categories/men-hoodies")).json()["data"]
    assert [b["slug"] for b in detail["breadcrumbs"]] == ["men", "men-hoodies"]
    assert detail["seo"]["canonicalUrl"].endswith("/category/men-hoodies")


async def test_parent_category_includes_children(client, catalog):
    items = (await client.get("/api/v1/products", params={"category": "men"})).json()["data"]["items"]
    assert {p["slug"] for p in items} == {"classic-black-hoodie", "puffer-jacket"}


async def test_filters_and_sorting(client, catalog):
    by_size = (await client.get("/api/v1/products", params={"size": "XL"})).json()["data"]["items"]
    assert by_size == []  # XL hoodie exists but is out of stock

    by_price = (await client.get("/api/v1/products", params={"maxPrice": 5000})).json()["data"]["items"]
    assert [p["slug"] for p in by_price] == ["classic-black-hoodie"]

    express = (await client.get("/api/v1/products", params={"express": True})).json()["data"]["items"]
    assert [p["slug"] for p in express] == ["classic-black-hoodie"]

    search = (await client.get("/api/v1/products", params={"q": "fleece"})).json()["data"]["items"]
    assert [p["slug"] for p in search] == ["classic-black-hoodie"]

    cheapest_first = (await client.get("/api/v1/products", params={"sort": "price_asc"})).json()["data"]
    assert [p["price"] for p in cheapest_first["items"]] == [3500, 9000]
    assert cheapest_first["meta"]["totalItems"] == 2


async def test_product_detail_has_variants_and_seo(client, catalog):
    product = (await client.get("/api/v1/products/classic-black-hoodie")).json()["data"]
    assert product["discountPercent"] == 22
    assert product["availableSizes"] == ["M", "L", "XL"]
    assert product["inStock"] is True
    assert {v["sku"]: v["inStock"] for v in product["variants"]}["HD-BLK-XL"] is False
    assert product["seo"]["title"] == "Classic Black Hoodie | Bazaura.pk"
    assert [b["slug"] for b in product["breadcrumbs"]] == ["men", "men-hoodies"]


async def test_unknown_product_404(client, catalog):
    response = await client.get("/api/v1/products/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


async def test_sitemap_and_config(client, catalog):
    sitemap = (await client.get("/api/v1/seo/sitemap")).json()["data"]
    assert "/product/classic-black-hoodie" in [p["path"] for p in sitemap["products"]]

    config = (await client.get("/api/v1/storefront/config")).json()["data"]
    assert config["expressDeliveryHours"] == 3
    assert config["paymentMethods"] == ["CASH_ON_DELIVERY"]
    express = next(o for o in config["deliveryOptions"] if o["type"] == "EXPRESS")
    assert express["estimate"] == "Delivered within 3 hours"


async def test_home_feed(client, catalog):
    home = (await client.get("/api/v1/storefront/home")).json()["data"]
    assert home["featuredCategories"][0]["slug"] == "men"
    assert home["onSale"][0]["slug"] == "classic-black-hoodie"


async def test_reviews_one_per_customer(client, catalog, customer):
    payload = {"rating": 5, "comment": "Great quality fleece"}
    first = await client.post("/api/v1/products/classic-black-hoodie/reviews", headers=customer, json=payload)
    assert first.status_code == 201
    assert first.json()["data"]["isVerifiedPurchase"] is False
    again = await client.post("/api/v1/products/classic-black-hoodie/reviews", headers=customer, json=payload)
    assert again.status_code == 409

    product = (await client.get("/api/v1/products/classic-black-hoodie")).json()["data"]
    assert product["reviewCount"] == 1 and product["ratingAvg"] == 5.0
