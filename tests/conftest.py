"""
Test setup: every test gets a fresh in-memory SQLite database and an HTTP
client wired to the app. OTPs are fixed to 123456 so login is deterministic.
"""

import os

os.environ.update(
    ENVIRONMENT="test",
    DATABASE_URL="sqlite+aiosqlite:///:memory:",
    OTP_FIXED_CODE="123456",
    SECRET_KEY="test-secret-key-that-is-long-enough-123456",
    EXPRESS_DELIVERY_HOURS="3",
    EXPRESS_DELIVERY_CITIES='["Lahore"]',
)

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, Category, Product, ProductVariant, User, Voucher  # noqa: E402
from app.models.enums import DiscountType, Gender, Season, UserRole  # noqa: E402

OTP = "123456"


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield factory
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture
async def client(session_factory):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


@pytest.fixture
async def db(session_factory):
    async with session_factory() as session:
        yield session


async def login(client: AsyncClient, phone: str, full_name: str = "Test User") -> dict:
    response = await client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert response.status_code == 200, response.text
    response = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "code": OTP, "fullName": full_name})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['data']['accessToken']}"}


@pytest.fixture
async def customer(client) -> dict:
    return await login(client, "03001234567", "Ali Customer")


@pytest.fixture
async def admin(client, db) -> dict:
    headers = await login(client, "03111111111", "Admin")
    user = (await db.execute(User.__table__.select().where(User.phone == "+923111111111"))).first()
    await db.execute(User.__table__.update().where(User.id == user.id).values(role=UserRole.ADMIN))
    await db.commit()
    return headers


@pytest.fixture
async def catalog(db) -> dict:
    men = Category(name="Men", slug="men", is_featured=True)
    hoodies = Category(name="Hoodies", slug="men-hoodies", parent=men)
    hoodie = Product(
        title="Classic Black Hoodie",
        slug="classic-black-hoodie",
        category=hoodies,
        price=3500,
        compare_at_price=4500,
        gender=Gender.MEN,
        season=Season.WINTER,
        fabric="Fleece",
        images=["https://img.test/hoodie.jpg"],
        tags=["hoodie", "winter"],
        variants=[
            ProductVariant(sku="HD-BLK-M", size="M", color="Black", stock_quantity=5),
            ProductVariant(sku="HD-BLK-L", size="L", color="Black", stock_quantity=1),
            ProductVariant(sku="HD-BLK-XL", size="XL", color="Black", stock_quantity=0),
        ],
    )
    jacket = Product(
        title="Puffer Jacket",
        slug="puffer-jacket",
        category=men,
        price=9000,
        gender=Gender.MEN,
        season=Season.WINTER,
        is_express_eligible=False,
        variants=[ProductVariant(sku="PJ-NVY-L", size="L", color="Navy", stock_quantity=3)],
    )
    voucher = Voucher(
        code="WELCOME10", description="10% off", discount_type=DiscountType.PERCENT, value=10, max_discount=500
    )
    db.add_all([men, hoodies, hoodie, jacket, voucher])
    await db.commit()
    return {
        "hoodie": hoodie,
        "jacket": jacket,
        "hoodie_m": hoodie.variants[0],
        "hoodie_l": hoodie.variants[1],
        "hoodie_xl": hoodie.variants[2],
        "jacket_l": jacket.variants[0],
    }


async def add_address(client: AsyncClient, headers: dict, city: str = "Lahore") -> str:
    response = await client.post(
        "/api/v1/users/me/addresses",
        headers=headers,
        json={"fullName": "Ali", "phone": "03001234567", "addressLine1": "House 1", "area": "Gulberg", "city": city},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]
