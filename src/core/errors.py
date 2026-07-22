from typing import Any


class AppError(Exception):
    def __init__(
        self,
        code: str,
        detail: str,
        status: int = 500,
        context: dict[str, Any] | None = None,
    ):
        self.code = code
        self.detail = detail
        self.status = status
        self.context = context or {}
        super().__init__(self.detail)

    def to_dict(self) -> dict:
        return {"error": {"code": self.code, "detail": self.detail, **self.context}}


class AuthError(AppError):
    def __init__(self, subtype: str, detail: str, context: dict[str, Any] | None = None):
        super().__init__(code=f"auth_{subtype}", detail=detail, status=401, context=context)


class RateLimitError(AppError):
    def __init__(self, tier: str, retry_after: int):
        super().__init__(
            code="rate_limit_exceeded",
            detail=f"Rate limit exceeded for tier '{tier}'",
            status=429,
            context={"tier": tier, "retry_after": retry_after},
        )


class NotFoundError(AppError):
    def __init__(self, subtype: str, detail: str):
        super().__init__(code=f"not_found_{subtype}", detail=detail, status=404)


class ConflictError(AppError):
    def __init__(self, subtype: str, detail: str):
        super().__init__(code=f"conflict_{subtype}", detail=detail, status=409)
