"""
Application entrypoint.

Run locally with:  uvicorn app.main:app --reload
Interactive API docs: http://localhost:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import register_exception_handlers

logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.INFO)
# DEBUG is for our own code; keep chatty third-party libraries at WARNING.
for noisy in ("aiosqlite", "asyncio", "botocore", "boto3", "urllib3", "httpcore", "httpx"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Schema changes are applied with Alembic (`alembic upgrade head`), never on startup.
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Backend for the Bazaura.pk mobile app and website. All orders are Cash on Delivery.",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health", tags=["Health"], summary="Liveness check")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["Health"], summary="Readiness check (database reachable)")
    async def ready() -> dict:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}

    return app


app = create_app()
