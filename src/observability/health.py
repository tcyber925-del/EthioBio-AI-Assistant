import time
from dataclasses import dataclass
from threading import Lock
from typing import Optional

import structlog

from src.config import settings

logger = structlog.get_logger()


@dataclass
class ModuleHealth:
    name: str
    status: str = "healthy"
    details: str = ""
    last_error: Optional[str] = None
    _request_count: int = 0
    _error_count: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "details": self.details,
            "last_error": self.last_error,
            "request_count": self._request_count,
            "error_count": self._error_count,
        }


class ModuleHealthRegistry:
    def __init__(self):
        self._lock = Lock()
        self._modules: dict[str, ModuleHealth] = {}
        self._start_time: float = time.time()

    def register(self, name: str) -> ModuleHealth:
        with self._lock:
            if name not in self._modules:
                self._modules[name] = ModuleHealth(name=name)
            return self._modules[name]

    def get(self, name: str) -> Optional[ModuleHealth]:
        return self._modules.get(name)

    def record_request(self, name: str, error: bool = False) -> None:
        m = self.register(name)
        with self._lock:
            m._request_count += 1
            if error:
                m._error_count += 1

    def set_status(
        self, name: str, status: str, details: str = "", error: str | None = None
    ) -> None:
        m = self.register(name)
        with self._lock:
            m.status = status
            m.details = details
            if error:
                m.last_error = error

    def overall_status(self) -> str:
        with self._lock:
            has_unhealthy = any(m.status == "unhealthy" for m in self._modules.values())
            has_degraded = any(m.status == "degraded" for m in self._modules.values())
            if has_unhealthy:
                return "unhealthy"
            if has_degraded:
                return "degraded"
            return "healthy"

    def to_dict(self, include_details: bool = True) -> dict:
        return {
            "overall_status": self.overall_status(),
            "uptime_seconds": int(time.time() - self._start_time),
            "modules": [m.to_dict() for m in self._modules.values()] if include_details else [],
        }


health_registry: ModuleHealthRegistry | None = (
    ModuleHealthRegistry() if settings.observability_health_enabled else None
)
