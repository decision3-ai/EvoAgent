"""
Shared Redis rate limiter for public (unauthenticated) endpoints.

Per-IP hourly limit + global daily cap via Redis INCR/EXPIRE pipelines.
"""

from datetime import datetime, timezone

from fastapi import HTTPException, Request, status

from app.core.redis import get_redis


def get_client_ip(request: Request) -> str:
    # Use the rightmost X-Forwarded-For entry — appended by our nginx proxy,
    # not client-controlled. Leftmost is spoofable.
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[-1].strip()
    return request.client.host if request.client else 'unknown'


async def enforce_rate_limits(
    request: Request,
    *,
    prefix: str,
    per_hour: int,
    daily_cap: int,
    daily_detail: str,
) -> None:
    """
    Raise 429 if the per-IP hourly limit is hit, 503 if the global daily cap is hit.
    Per-IP is checked first so a single IP's rejected requests never consume the daily cap.
    """
    ip = get_client_ip(request)
    redis = get_redis()

    # 1. Per-IP hourly limit — keyed by IP + hour bucket
    hour_bucket = int(datetime.now(timezone.utc).timestamp()) // 3600
    ip_key = f'{prefix}:ip:{ip}:{hour_bucket}'
    async with redis.pipeline(transaction=True) as pipe:
        await pipe.incr(ip_key)
        await pipe.expire(ip_key, 3600)
        ip_count, _ = await pipe.execute()
    if ip_count > per_hour:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f'Rate limit exceeded: max {per_hour} requests per hour',
        )

    # 2. Global daily cap — keyed by UTC date; only reached by requests within the per-IP limit
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    daily_key = f'{prefix}:daily:{today}'
    async with redis.pipeline(transaction=True) as pipe:
        await pipe.incr(daily_key)
        await pipe.expire(daily_key, 86400)
        daily_count, _ = await pipe.execute()
    if daily_count > daily_cap:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=daily_detail,
        )
