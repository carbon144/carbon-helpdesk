"""Redis cache service for expensive queries."""
import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis = None


async def get_redis():
    """Get or create Redis connection."""
    global _redis
    if _redis is None:
        try:
            _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await _redis.ping()
        except Exception as e:
            logger.warning(f"Redis not available for caching: {e}")
            _redis = None
    return _redis


async def cache_get(key: str) -> Any | None:
    """Get value from cache. Returns None on miss or error."""
    r = await get_redis()
    if not r:
        return None
    try:
        val = await r.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 300):
    """Set value in cache with TTL. Fails silently."""
    r = await get_redis()
    if not r:
        return
    try:
        await r.set(key, json.dumps(value, default=str), ex=ttl_seconds)
    except Exception:
        pass


async def cache_delete_pattern(pattern: str):
    """Delete all keys matching pattern. Fails silently."""
    r = await get_redis()
    if not r:
        return
    try:
        keys = []
        async for key in r.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await r.delete(*keys)
    except Exception:
        pass
