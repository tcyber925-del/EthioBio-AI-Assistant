from collections.abc import Callable

import structlog

from src.config import settings

logger = structlog.get_logger()


class AlertThreshold:
    def __init__(
        self,
        name: str,
        severity: str,
        evaluate: Callable[[], bool],
        message: str,
        cooldown_seconds: float = 300.0,
    ):
        self.name = name
        self.severity = severity
        self.evaluate = evaluate
        self.message = message
        self.cooldown_seconds = cooldown_seconds
        self._last_fired: float = 0.0

    def check(self) -> bool:
        import time

        now = time.time()
        if now - self._last_fired < self.cooldown_seconds:
            return False
        if self.evaluate():
            self._last_fired = now
            return True
        return False


class AlertManager:
    def __init__(self):
        self._thresholds: list[AlertThreshold] = []

    def add_threshold(self, threshold: AlertThreshold) -> None:
        self._thresholds.append(threshold)

    def evaluate_all(self) -> list[str]:
        fired: list[str] = []
        for t in self._thresholds:
            if t.check():
                logger.warning("alert_fired", name=t.name, severity=t.severity, message=t.message)
                fired.append(t.name)
        return fired


alert_manager: AlertManager | None = (
    AlertManager() if settings.observability_alerting_enabled else None
)
