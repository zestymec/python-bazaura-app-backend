NEW_PRODUCT = {
    "title": "Fleece Tracksuit – Charcoal",
    "price": 6500,
    "gender": "MEN",
    "season": "WINTER",
    "fabric": "Fleece",
    "variants": [
        {"sku": "TS-CHR-M", "size": "M", "color": "Charcoal", "stockQuantity": 4},
        {"sku": "TS-CHR-L", "size": "L", "color": "Charcoal", "stockQuantity": 2},
    ],
}


async def test_customer_cannot_use_admin_endpoints(client, customer):
    response = await client.post("/api/v1/admin/products", headers=customer, json=NEW_PRODUCT)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INSUFFICIENT_ROLE"


async def test_admin_product_crud_with_slug_generation(client, admin, catalog):
    created = await client.post(
        "/api/v1/admin/products", headers=admin, json={**NEW_PRODUCT, "categoryId": catalog["hoodie"].category_id}
    )
    assert created.status_code == 201, created.text
    product = created.json()["data"]
    assert product["slug"] == "fleece-tracksuit-charcoal"
    assert len(product["variants"]) == 2

    duplicate = await client.post("/api/v1/admin/products", headers=admin, json={**NEW_PRODUCT, "variants": []})
    assert duplicate.json()["data"]["slug"] == "fleece-tracksuit-charcoal-2"

    clash = await client.post(
        f"/api/v1/admin/products/{product['id']}/variants", headers=admin, json={"sku": "TS-CHR-M", "size": "XL"}
    )
    assert clash.status_code == 409

    variant_id = product["variants"][0]["id"]
    restock = await client.patch(f"/api/v1/admin/variants/{variant_id}", headers=admin, json={"stockQuantity": 20})
    assert restock.json()["data"]["stockQuantity"] == 20

    await client.delete(f"/api/v1/admin/products/{product['id']}", headers=admin)
    public = await client.get(f"/api/v1/products/{product['slug']}")
    assert public.status_code == 404  # archived products disappear from the store


async def test_admin_voucher_and_content(client, admin):
    voucher = await client.post(
        "/api/v1/admin/vouchers",
        headers=admin,
        json={"code": "winter500", "discountType": "FLAT", "value": 500, "minOrderAmount": 3000},
    )
    assert voucher.json()["data"]["code"] == "WINTER500"

    banner = await client.post(
        "/api/v1/admin/content",
        headers=admin,
        json={
            "contentType": "BANNER",
            "title": "Winter Collection",
            "imageUrl": "https://img.test/winter.jpg",
            "targetType": "COLLECTION",
            "targetValue": "season=WINTER",
        },
    )
    assert banner.status_code == 201
    home = (await client.get("/api/v1/storefront/home")).json()["data"]
    assert home["banners"][0]["title"] == "Winter Collection"


async def test_admin_can_promote_staff(client, admin, customer):
    users = (await client.get("/api/v1/admin/users", headers=admin, params={"q": "3001234567"})).json()["data"]["items"]
    assert len(users) == 1
    updated = await client.patch(f"/api/v1/admin/users/{users[0]['id']}", headers=admin, json={"role": "staff"})
    assert updated.json()["data"]["role"] == "staff"
    # staff can now see orders but not create products
    assert (await client.get("/api/v1/admin/orders", headers=customer)).status_code == 200
    assert (await client.post("/api/v1/admin/products", headers=customer, json=NEW_PRODUCT)).status_code == 403


async def test_wishlist_is_idempotent(client, customer, catalog):
    product_id = catalog["hoodie"].id
    for _ in range(2):
        assert (await client.put(f"/api/v1/wishlist/{product_id}", headers=customer)).status_code == 200
    items = (await client.get("/api/v1/wishlist", headers=customer)).json()["data"]
    assert [p["id"] for p in items] == [product_id]

    await client.delete(f"/api/v1/wishlist/{product_id}", headers=customer)
    assert (await client.get("/api/v1/wishlist", headers=customer)).json()["data"] == []
