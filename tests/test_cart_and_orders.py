from sqlalchemy import select

from app.models.catalog import ProductVariant
from tests.conftest import add_address


async def quote(client, **body):
    return (await client.post("/api/v1/cart/quote", json=body)).json()["data"]


async def test_cart_quote_with_voucher_and_fees(client, catalog):
    data = await quote(client, items=[{"variantId": catalog["hoodie_m"].id, "quantity": 2}], voucherCode="welcome10")
    assert data["subtotal"] == 7000
    assert data["discount"] == 500  # 10% = 700, capped at 500
    assert data["deliveryFee"] == 199  # standard, below free-shipping threshold
    assert data["total"] == 7000 - 500 + 199
    assert data["canCheckout"] is True
    assert data["amountToFreeShipping"] == 3000


async def test_free_shipping_over_threshold(client, catalog):
    data = await quote(client, items=[{"variantId": catalog["jacket_l"].id, "quantity": 2}])
    assert data["subtotal"] == 18000 and data["deliveryFee"] == 0


async def test_stock_problems_block_checkout(client, catalog):
    data = await quote(
        client,
        items=[
            {"variantId": catalog["hoodie_l"].id, "quantity": 3},
            {"variantId": catalog["hoodie_xl"].id, "quantity": 1},
            {"variantId": "var_missing", "quantity": 1},
        ],
    )
    assert {i["code"] for i in data["issues"]} == {"INSUFFICIENT_STOCK", "OUT_OF_STOCK", "VARIANT_NOT_FOUND"}
    assert data["canCheckout"] is False


async def test_express_rules(client, catalog):
    item = [{"variantId": catalog["hoodie_m"].id, "quantity": 1}]
    lahore = await quote(client, items=item, deliveryType="EXPRESS", city="lahore")
    assert lahore["canCheckout"] is True
    assert lahore["deliveryFee"] == 299
    assert lahore["deliveryEstimate"] == "Delivered within 3 hours"

    karachi = await quote(client, items=item, deliveryType="EXPRESS", city="Karachi")
    assert karachi["issues"][0]["code"] == "EXPRESS_UNAVAILABLE"

    not_eligible = await quote(
        client, items=[{"variantId": catalog["jacket_l"].id, "quantity": 1}], deliveryType="EXPRESS", city="Lahore"
    )
    assert not_eligible["issues"][0]["code"] == "EXPRESS_UNAVAILABLE"


async def test_place_order_reserves_stock_and_cancel_restores_it(client, catalog, customer, db):
    address_id = await add_address(client, customer)
    response = await client.post(
        "/api/v1/orders",
        headers=customer,
        json={
            "items": [{"variantId": catalog["hoodie_m"].id, "quantity": 2}],
            "addressId": address_id,
            "deliveryType": "EXPRESS",
            "voucherCode": "WELCOME10",
        },
    )
    assert response.status_code == 201, response.text
    order = response.json()["data"]
    assert order["orderNumber"].startswith("BZ-")
    assert order["paymentMethod"] == "CASH_ON_DELIVERY"
    assert order["total"] == 7000 - 500 + 299
    assert order["timeline"][0] == {**order["timeline"][0], "status": "PLACED", "isCompleted": True}
    assert order["shippingAddress"]["city"] == "Lahore"

    variant_id = catalog["hoodie_m"].id

    async def stock():
        db.expire_all()
        return (
            await db.execute(select(ProductVariant.stock_quantity).where(ProductVariant.id == variant_id))
        ).scalar_one()

    assert await stock() == 3

    listing = (await client.get("/api/v1/orders", headers=customer)).json()["data"]
    assert listing["items"][0]["itemCount"] == 2

    cancelled = await client.post(
        f"/api/v1/orders/{order['id']}/cancel", headers=customer, json={"reason": "Changed mind"}
    )
    assert cancelled.json()["data"]["status"] == "CANCELLED"
    assert await stock() == 5

    again = await client.post(f"/api/v1/orders/{order['id']}/cancel", headers=customer)
    assert again.status_code == 409


async def test_order_rejected_when_cart_invalid(client, catalog, customer):
    address_id = await add_address(client, customer)
    response = await client.post(
        "/api/v1/orders",
        headers=customer,
        json={"items": [{"variantId": catalog["hoodie_l"].id, "quantity": 5}], "addressId": address_id},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CART_INVALID"


async def test_admin_moves_order_through_lifecycle(client, catalog, customer, admin):
    address_id = await add_address(client, customer)
    order = (
        await client.post(
            "/api/v1/orders",
            headers=customer,
            json={"items": [{"variantId": catalog["hoodie_m"].id, "quantity": 1}], "addressId": address_id},
        )
    ).json()["data"]

    skip = await client.patch(f"/api/v1/admin/orders/{order['id']}/status", headers=admin, json={"status": "DELIVERED"})
    assert skip.status_code == 409

    for status in ("CONFIRMED", "PACKED", "SHIPPED", "DELIVERED"):
        response = await client.patch(
            f"/api/v1/admin/orders/{order['id']}/status", headers=admin, json={"status": status}
        )
        assert response.status_code == 200, response.text

    detail = (await client.get(f"/api/v1/orders/{order['id']}", headers=customer)).json()["data"]
    assert all(step["isCompleted"] for step in detail["timeline"])
    assert detail["canCancel"] is False

    # Delivered order turns the review into a verified purchase
    review = await client.post(
        "/api/v1/products/classic-black-hoodie/reviews", headers=customer, json={"rating": 4, "comment": "Fits well"}
    )
    assert review.json()["data"]["isVerifiedPurchase"] is True


async def test_customer_cannot_see_others_orders(client, catalog, customer):
    from tests.conftest import login

    address_id = await add_address(client, customer)
    order = (
        await client.post(
            "/api/v1/orders",
            headers=customer,
            json={"items": [{"variantId": catalog["hoodie_m"].id, "quantity": 1}], "addressId": address_id},
        )
    ).json()["data"]
    other = await login(client, "03008888888")
    assert (await client.get(f"/api/v1/orders/{order['id']}", headers=other)).status_code == 404
