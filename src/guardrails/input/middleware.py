import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from src.config import settings
from src.guardrails.input.rate_limiter import RateLimiter

logger = structlog.get_logger()


def add_rate_limit_middleware(app: FastAPI, redis_client: Redis) -> None:
    limiter = RateLimiter(redis_client)

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        if not settings.rate_limit_enabled:
            return await call_next(request)

        if not request.url.path.startswith("/chat"):
            return await call_next(request)

        user_id = request.headers.get("X-User-ID", "")
        if user_id:
            allowed = await limiter.check(
                f"user:{user_id}:chat",
                settings.rate_limit_user_max,
                settings.rate_limit_user_window,
            )
            if not allowed:
                remaining = await limiter.get_remaining(
                    f"user:{user_id}:chat",
                    settings.rate_limit_user_max,
                    settings.rate_limit_user_window,
                )
                logger.warning("rate_limit_exceeded", user_id=user_id, scope="user")
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Please wait before sending another message."
                    },
                    headers={
                        "Retry-After": str(settings.rate_limit_user_window),
                        "X-RateLimit-Limit": str(settings.rate_limit_user_max),
                        "X-RateLimit-Remaining": str(remaining),
                    },
                )

        forwarded = request.headers.get("X-Forwarded-For", "")
        ip = (
            forwarded.split(",")[0].strip()
            if forwarded
            else request.client.host
            if request.client
            else "unknown"
        )
        allowed = await limiter.check(
            f"ip:{ip}:chat",
            settings.rate_limit_ip_max,
            settings.rate_limit_ip_window,
        )
        if not allowed:
            remaining = await limiter.get_remaining(
                f"ip:{ip}:chat",
                settings.rate_limit_ip_max,
                settings.rate_limit_ip_window,
            )
            logger.warning("rate_limit_exceeded", ip=ip, scope="ip")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please wait before sending another message."
                },
                headers={
                    "Retry-After": str(settings.rate_limit_ip_window),
                    "X-RateLimit-Limit": str(settings.rate_limit_ip_max),
                    "X-RateLimit-Remaining": str(remaining),
                },
            )

        return await call_next(request)
