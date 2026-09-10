"""
Bazaura.pk - Redis Cache & Rate Limiting Module
Provides an asynchronous Redis client pool for caching home feeds,
storing active OTP verification codes, and tracking rate limits.
"""

from typing import Optional
import redis.asyncio as aioredis
from app.core.config import settings

redis_pool: Optional[aioredis.Redis] = None


async def get_redis_client() -> aioredis.Redis:
    """
    Returns or initializes the global asynchronous Redis connection.
    """
    global redis_pool
    if redis_pool is None:
        redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    return redis_pool


async def close_redis():
    """
    Closes the global Redis connection pool gracefully on application shutdown.
    """
    global redis_pool
    if redis_pool is not None:
        await redis_pool.close()
        redis_pool = None
