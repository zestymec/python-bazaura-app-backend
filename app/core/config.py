"""
Bazaura.pk - Core Configuration Module
Defines strongly-typed environment settings using Pydantic Settings (v2).
Handles database URLs, JWT security configurations, Redis connections,
and Pakistani quick-commerce logistics thresholds.
"""

from typing import List, Optional
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Core Application
    PROJECT_NAME: str = "Bazaura.pk Quick-Commerce & Concierge Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # CORS configuration
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # Security & JWT Tokens
    # Used for HMAC-SHA256 signing of JWT access & refresh tokens
    SECRET_KEY: str = "bazaura_super_secret_production_key_change_in_env_minimum_32_characters"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 Hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30     # 30 Days

    # Database Configuration (PostgreSQL 16+ via SQLAlchemy 2.0 Asyncpg)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "bazaura_db"
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    @computed_field
    def async_database_url(self) -> str:
        """
        Builds the asynchronous PostgreSQL connection string using asyncpg driver.
        If SQLALCHEMY_DATABASE_URI is explicitly set in .env (e.g. for testing or SQLite async),
        it takes precedence.
        """
        if self.SQLALCHEMY_DATABASE_URI:
            return self.SQLALCHEMY_DATABASE_URI
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis Cache & Broker Configuration
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery Asynchronous Workers
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Quick-Commerce Logistics Business Rules (in PKR)
    # ⚡ 2-Hour Express Lahore: Rs. 299 for subtotal < 10,000 PKR; Free (Rs. 0) over 10,000 PKR
    # 📦 Nationwide Standard Delivery: Rs. 199 for subtotal < 10,000 PKR; Free (Rs. 0) over 10,000 PKR
    FREE_SHIPPING_THRESHOLD_PKR: int = 10000
    LAHORE_EXPRESS_DELIVERY_FEE_PKR: int = 299
    NATIONWIDE_STANDARD_DELIVERY_FEE_PKR: int = 199

    # AWS S3 / MinIO Object Storage
    AWS_ACCESS_KEY_ID: str = "mock_access_key"
    AWS_SECRET_ACCESS_KEY: str = "mock_secret_key"
    AWS_REGION: str = "eu-west-1"
    AWS_S3_BUCKET_NAME: str = "bazaura-media-bucket"
    S3_PUBLIC_BASE_URL: str = "https://media.bazaura.pk"

    # Pakistani Payment Gateways
    JAZZCASH_MERCHANT_ID: str = "MOCK_JAZZCASH_MERCHANT"
    JAZZCASH_PASSWORD: str = "MOCK_PASSWORD"
    JAZZCASH_HASH_SECRET: str = "MOCK_INTEGRITY_SALT"
    EASYPAISA_STORE_ID: str = "MOCK_EASYPAISA_STORE"
    EASYPAISA_HASH_KEY: str = "MOCK_EASYPAISA_KEY"

    # SMS OTP & Notifications (Pakistan Providers: Zong / Jazz / Twilio)
    SMS_GATEWAY_API_KEY: str = "MOCK_SMS_GATEWAY_KEY"
    SMS_SENDER_ID: str = "BAZAURA"
    FCM_SERVER_KEY: str = "MOCK_FCM_SERVER_KEY"
    OTP_EXPIRY_SECONDS: int = 120
    OTP_RESEND_COOLDOWN_SECONDS: int = 60


settings = Settings()
