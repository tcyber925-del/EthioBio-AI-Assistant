import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from src.core.errors import RateLimitError
from src.guardrails.input.rate_limiter import TieredRateLimiter

logger = structlog.get_logger()


SKIP_PATHS = frozenset({"/health", "/liveness", "/readiness", "/metrics", "/ping"})


def add_rate_limit_middleware(app: FastAPI, redis_client: Redis):
    limiter = TieredRateLimiter(redis_client)

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        user_id = None
        access_cookie = request.cookies.get("access_token")
        if access_cookie:
            try:
                from jose import jwt as jose_jwt

                from src.config import settings as app_settings

                payload = jose_jwt.decode(
                    access_cookie,
                    app_settings.jwt_secret,
                    algorithms=[app_settings.jwt_algorithm],
                    options={"verify_exp": False},
                )
                user_id = payload.get("sub")
            except Exception:
                pass

        raw_ip = request.headers.get("X-Forwarded-For", "")
        if raw_ip:
            ip = raw_ip.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        key = f"{user_id}:{ip}" if user_id else ip

        allowed, headers = await limiter.check_and_get_headers(
            key, request.url.path, request.method
        )
        if not allowed:
            tier = limiter.resolve_tier(request.url.path, request.method)
            logger.warning("rate_limit_exceeded", path=request.url.path, tier=tier)
            err = RateLimitError(tier, retry_after=int(headers.get("Retry-After", 60)))
            return JSONResponse(
                status_code=429,
                content=err.to_dict(),
                headers=headers,
            )

        response = await call_next(request)
        for h, v in headers.items():
            response.headers[h] = v
        return response

    return limiter
