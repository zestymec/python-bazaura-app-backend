"""
Bazaura.pk - FastAPI Application Entrypoint
Initialises the FastAPI app, adds CORS middleware, registers the versioned API router,
and ensures graceful shutdown of DB and Redis resources.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base, get_db
from app.core.redis import get_redis_client, close_redis
from app.api.v1 import router as api_v1_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Global CORS configuration – allow all origins for development (tighten in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the version‑1 API router under the configured prefix (e.g. /api/v1)
app.include_router(api_v1_router, prefix=settings.API_V1_STR)

# ---------------------------------------------------------------------------
# Application Lifespan Events
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup() -> None:
    """Create DB tables (if missing) and initialise Redis client on startup.
    In production you would run Alembic migrations separately; this is a safety net
    for local development.
    """
    # Ensure all tables exist – useful for a fresh dev DB
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Initialise Redis connection pool
    await get_redis_client()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Close DB engine and Redis pool gracefully on app termination."""
    await engine.dispose()
    await close_redis()

# ---------------------------------------------------------------------------
# Root health‑check endpoint – useful for Kubernetes liveness/readiness probes
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    return {"status": "ok", "service": "Bazaura.pk FastAPI Backend"}
