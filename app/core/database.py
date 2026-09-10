"""
Bazaura.pk - Database Management Module
Implements SQLAlchemy 2.0 modern asynchronous engine, session factory,
and dependency injection provider for FastAPI endpoints.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Configure SQLAlchemy Async Engine
# echo=settings.DEBUG logs generated SQL queries during development
# pool_pre_ping validates connection health before handing out sessions
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    future=True
)

# Modern SQLAlchemy 2.0 async sessionmaker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy 2.0 declarative database models in Bazaura.pk.
    """
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an asynchronous database session per request.
    Ensures safe session closure and automatic rollback on unhandled exceptions.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
