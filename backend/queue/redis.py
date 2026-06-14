# queue/redis.py
from __future__ import annotations

from redis.asyncio import ConnectionPool, Redis

from settings import Settings

_pool: ConnectionPool | None = None


def init_redis_pool(settings: Settings) -> ConnectionPool:
    global _pool
    _pool = ConnectionPool.from_url(
        settings.redis.url,
        max_connections=settings.redis.max_connections,
        socket_timeout=settings.redis.socket_timeout,
        decode_responses=settings.redis.decode_responses,
    )
    return _pool


def get_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError("Redis connection pool has not been initialized")
    return _pool


def get_redis_client(settings: Settings | None = None) -> Redis:
    global _pool
    if _pool is None:
        if settings is None:
            raise RuntimeError("Redis connection pool has not been initialized")
        init_redis_pool(settings)
    return Redis(connection_pool=_pool)


async def close_redis_pool(pool: ConnectionPool | None = None) -> None:
    global _pool
    target = pool or _pool
    if target is not None:
        await target.disconnect()
    _pool = None


def get_sync_redis_client(settings: Settings):
    import redis as sync_redis

    return sync_redis.Redis.from_url(
        settings.redis.url,
        decode_responses=settings.redis.decode_responses,
        socket_timeout=settings.redis.socket_timeout,
    )