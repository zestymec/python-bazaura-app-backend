"""
Application settings.

Every value can be overridden with an environment variable of the same name
(or a line in `.env`). Business rules that the brand may want to tune — delivery
fees, express delivery hours, free-shipping threshold — live here so they can be
changed without touching code.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULT_SECRET = "change-me-in-env-this-is-not-a-real-secret-key"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Application -------------------------------------------------------
    PROJECT_NAME: str = "Bazaura.pk API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development | staging | production | test
    DEBUG: bool = False
    SITE_URL: str = "https://bazaura.pk"  # used for canonical URLs in SEO metadata

    # Origins allowed to call the API from a browser (Next.js site, admin, Expo web).
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8081"]

    # --- Security ----------------------------------------------------------
    SECRET_KEY: str = _INSECURE_DEFAULT_SECRET
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # --- Database ----------------------------------------------------------
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/bazaura"
    SQL_ECHO: bool = False

    # --- OTP login ---------------------------------------------------------
    OTP_LENGTH: int = 6
    OTP_EXPIRY_SECONDS: int = 300
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    OTP_MAX_ATTEMPTS: int = 5
    OTP_MAX_REQUESTS_PER_WINDOW: int = 3
    OTP_REQUEST_WINDOW_MINUTES: int = 15
    # Development/test only: every OTP equals this code. Refused in production.
    OTP_FIXED_CODE: Optional[str] = None

    # --- Delivery & pricing (PKR) -----------------------------------------
    FREE_SHIPPING_THRESHOLD_PKR: int = 10000
    STANDARD_DELIVERY_FEE_PKR: int = 199
    STANDARD_DELIVERY_ESTIMATE: str = "2-4 working days"
    EXPRESS_DELIVERY_FEE_PKR: int = 299
    EXPRESS_DELIVERY_HOURS: int = 3
    EXPRESS_DELIVERY_CITIES: List[str] = ["Lahore"]
    GIFT_WRAP_FEE_PKR: int = 0

    # --- Custom requests ---------------------------------------------------
    CUSTOM_REQUEST_QUOTE_VALID_DAYS: int = 2

    # --- Object storage (S3 compatible: AWS S3, Cloudflare R2, MinIO) ------
    STORAGE_ENDPOINT_URL: Optional[str] = None  # None = AWS S3
    STORAGE_ACCESS_KEY_ID: str = ""
    STORAGE_SECRET_ACCESS_KEY: str = ""
    STORAGE_REGION: str = "auto"
    STORAGE_BUCKET: str = "bazaura-media"
    STORAGE_PUBLIC_BASE_URL: str = "https://media.bazaura.pk"

    # --- Notifications -----------------------------------------------------
    SMS_PROVIDER: str = "console"  # console = log messages instead of sending
    SMS_API_KEY: str = ""
    SMS_SENDER_ID: str = "BAZAURA"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def express_cities_normalized(self) -> set[str]:
        return {city.strip().lower() for city in self.EXPRESS_DELIVERY_CITIES}

    def is_express_city(self, city: Optional[str]) -> bool:
        return bool(city) and city.strip().lower() in self.express_cities_normalized

    @model_validator(mode="after")
    def _check_production_safety(self) -> "Settings":
        if self.is_production:
            if self.SECRET_KEY == _INSECURE_DEFAULT_SECRET or len(self.SECRET_KEY) < 32:
                raise ValueError("SECRET_KEY must be set to a random value of 32+ characters in production")
            if self.OTP_FIXED_CODE:
                raise ValueError("OTP_FIXED_CODE must not be set in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
