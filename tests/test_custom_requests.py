from tests.conftest import add_address

GIFT = {
    "requestType": "GIFT",
    "itemName": "Grey hoodie size L",
    "description": "Birthday gift for my brother",
    "quantity": 2,
    "deliveryType": "EXPRESS",
    "deliveryAddress": {
        "fullName": "Hamza",
        "phone": "03211234567",
        "addressLine1": "House 9, Street 3",
        "area": "DHA Phase 5",
        "city": "Lahore",
    },
    "giftMessage": "Happy birthday!",
    "giftWrap": True,
    "hideSender": True,
}


async def test_gift_request_quote_accept_flow(client, customer, admin):
    created = await client.post("/api/v1/custom-requests", headers=customer, json=GIFT)
    assert created.status_code == 201, created.text
    request = created.json()["data"]
    assert request["requestNumber"].startswith("RQ-")
    assert request["status"] == "SUBMITTED"
    assert request["deliveryAddress"]["phone"] == "+923211234567"

    # Customer cannot accept before a quote exists
    early = await client.post(f"/api/v1/custom-requests/{request['id']}/accept-quote", headers=customer)
    assert early.status_code == 409

    quoted = await client.post(
        f"/api/v1/admin/custom-requests/{request['id']}/quote",
        headers=admin,
        json={"unitPrice": 2500, "notes": "Available in stock"},
    )
    assert quoted.status_code == 200, quoted.text
    quote = quoted.json()["data"]["quote"]
    assert quote["itemPrice"] == 5000
    assert quote["deliveryFee"] == 299  # express fee, below free-shipping threshold
    assert quote["total"] == 5299

    accepted = (await client.post(f"/api/v1/custom-requests/{request['id']}/accept-quote", headers=customer)).json()[
        "data"
    ]
    assert accepted["status"] == "CONFIRMED"

    order = (await client.get(f"/api/v1/orders/{accepted['orderId']}", headers=customer)).json()["data"]
    assert order["source"] == "CUSTOM_REQUEST"
    assert order["total"] == 5299
    assert order["items"][0]["quantity"] == 2 and order["items"][0]["lineTotal"] == 5000
    assert order["shippingAddress"]["fullName"] == "Hamza"
    assert "GIFT ORDER" in order["customerNote"] and "hide sender name" in order["customerNote"]


async def test_custom_item_with_saved_address_and_cancel(client, customer):
    address_id = await add_address(client, customer, city="Karachi")
    body = {"itemName": "Leather jacket", "description": "Brown, size M", "addressId": address_id}
    request = (await client.post("/api/v1/custom-requests", headers=customer, json=body)).json()["data"]
    assert request["requestType"] == "CUSTOM_ITEM"

    cancelled = await client.post(f"/api/v1/custom-requests/{request['id']}/cancel", headers=customer)
    assert cancelled.json()["data"]["status"] == "CANCELLED"


async def test_express_custom_request_outside_express_city_rejected(client, customer):
    body = {**GIFT, "deliveryAddress": {**GIFT["deliveryAddress"], "city": "Multan"}}
    response = await client.post("/api/v1/custom-requests", headers=customer, json=body)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EXPRESS_UNAVAILABLE"


async def test_request_needs_an_address(client, customer):
    body = {"itemName": "Something", "description": "Details here"}
    response = await client.post("/api/v1/custom-requests", headers=customer, json=body)
    assert response.status_code == 422
