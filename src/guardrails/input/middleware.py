import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.core.errors import RateLimitError
from src.guardrails.input.rate_limiter import TieredRateLimiter

logger = structlog.get_logger()


SKIP_PATHS = frozenset({"/health", "/liveness", "/readiness", "/metrics", "/ping"})


def add_rate_limit_middleware(app: FastAPI, redis_url: str):
    limiter = TieredRateLimiter(redis_url)

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        user_id = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from src.auth.clerk import extract_user_id_unverified

                user_id = await extract_user_id_unverified(auth_header[7:])
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
