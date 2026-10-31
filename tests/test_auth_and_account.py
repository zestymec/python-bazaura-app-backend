from tests.conftest import OTP, add_address, login


async def test_health(client):
    response = await client.get("/health")
    assert response.json() == {"status": "ok"}


async def test_otp_login_creates_user_and_normalizes_phone(client):
    await client.post("/api/v1/auth/otp/request", json={"phone": "0300-7654321"})
    response = await client.post("/api/v1/auth/otp/verify", json={"phone": "+92 300 7654321", "code": OTP})
    body = response.json()
    assert response.status_code == 200
    assert body["data"]["isNewUser"] is True
    assert body["data"]["user"]["phone"] == "+923007654321"
    assert body["data"]["refreshToken"]


async def test_wrong_otp_is_rejected(client):
    await client.post("/api/v1/auth/otp/request", json={"phone": "03007654321"})
    response = await client.post("/api/v1/auth/otp/verify", json={"phone": "03007654321", "code": "000000"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "OTP_INVALID"


async def test_otp_resend_cooldown(client):
    await client.post("/api/v1/auth/otp/request", json={"phone": "03007654321"})
    response = await client.post("/api/v1/auth/otp/request", json={"phone": "03007654321"})
    assert response.status_code == 429


async def test_invalid_phone_returns_validation_envelope(client):
    response = await client.post("/api/v1/auth/otp/request", json={"phone": "12345"})
    assert response.status_code == 422
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_refresh_token(client):
    await client.post("/api/v1/auth/otp/request", json={"phone": "03007654321"})
    tokens = (await client.post("/api/v1/auth/otp/verify", json={"phone": "03007654321", "code": OTP})).json()["data"]
    response = await client.post("/api/v1/auth/refresh", json={"refreshToken": tokens["refreshToken"]})
    assert response.status_code == 200
    # An access token must not work as a refresh token
    bad = await client.post("/api/v1/auth/refresh", json={"refreshToken": tokens["accessToken"]})
    assert bad.status_code == 401


async def test_profile_requires_auth(client):
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


async def test_profile_and_addresses(client, customer):
    response = await client.patch("/api/v1/users/me", headers=customer, json={"email": "ali@example.com"})
    assert response.json()["data"]["email"] == "ali@example.com"

    first = await add_address(client, customer, city="Lahore")
    second = await add_address(client, customer, city="Karachi")
    addresses = (await client.get("/api/v1/users/me/addresses", headers=customer)).json()["data"]
    assert [a["id"] for a in addresses] == [first, second]
    assert addresses[0]["isDefault"] is True  # first address becomes default
    assert addresses[0]["isExpressEligible"] is True
    assert addresses[1]["isExpressEligible"] is False

    await client.patch(f"/api/v1/users/me/addresses/{second}", headers=customer, json={"isDefault": True})
    await client.delete(f"/api/v1/users/me/addresses/{second}", headers=customer)
    addresses = (await client.get("/api/v1/users/me/addresses", headers=customer)).json()["data"]
    assert len(addresses) == 1 and addresses[0]["isDefault"] is True


async def test_cannot_touch_someone_elses_address(client, customer):
    address_id = await add_address(client, customer)
    other = await login(client, "03009999999")
    response = await client.delete(f"/api/v1/users/me/addresses/{address_id}", headers=other)
    assert response.status_code == 404
