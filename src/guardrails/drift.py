import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

import structlog

from src.config import settings

logger = structlog.get_logger()


@dataclass
class DriftWindow:
    total_checks: int = 0
    triggered_count: int = 0
    trigger_rate: float = 0.0
    timestamp: float = 0.0


@dataclass
class DriftAlert:
    layer: str
    current_rate: float
    baseline_rate: float
    drift: float
    message: str


class DriftMonitor:
    def __init__(self):
        self._enabled = settings.drift_monitor_enabled
        self._window_size = settings.drift_monitor_window
        self._threshold = settings.drift_alert_threshold
        self._baselines: dict[str, float] = {}
        self._windows: dict[str, DriftWindow] = defaultdict(DriftWindow)
        self._alerts: list[DriftAlert] = []

    def record_check(self, layer: str, triggered: bool):
        if not self._enabled:
            return

        now = time.time()
        w = self._windows[layer]
        if w.timestamp > 0 and now - w.timestamp > 3600:
            w.total_checks = 0
            w.triggered_count = 0
            w.timestamp = now
        elif w.timestamp == 0:
            w.timestamp = now

        w.total_checks += 1
        if triggered:
            w.triggered_count += 1

        w.trigger_rate = w.triggered_count / w.total_checks if w.total_checks > 0 else 0.0

    def get_trigger_rate(self, layer: str) -> Optional[float]:
        w = self._windows.get(layer)
        if w and w.total_checks >= 10:
            return w.trigger_rate
        return None

    def check_drift(self, layer: str) -> Optional[DriftAlert]:
        if not self._enabled:
            return None

        current_rate = self.get_trigger_rate(layer)
        if current_rate is None:
            return None

        baseline = self._baselines.get(layer)
        if baseline is None:
            self._baselines[layer] = current_rate
            return None

        drift = abs(current_rate - baseline)
        if drift > self._threshold and baseline > 0.01:
            alert = DriftAlert(
                layer=layer,
                current_rate=current_rate,
                baseline_rate=baseline,
                drift=drift,
                message=(
                    f"Guardrail layer '{layer}' drift detected: "
                    f"{current_rate:.2%} vs baseline {baseline:.2%} (Δ={drift:.2%})"
                ),
            )
            self._alerts.append(alert)
            logger.warning(
                "guardrail_drift_alert",
                layer=layer,
                drift=drift,
                current=current_rate,
                baseline=baseline,
            )
            return alert

        return None

    def rebaseline(self, layer: str):
        rate = self.get_trigger_rate(layer)
        if rate is not None:
            old = self._baselines.get(layer)
            self._baselines[layer] = rate
            logger.info("guardrail_rebaseline", layer=layer, old=old, new=rate)

    def get_alerts(self, clear: bool = False) -> list[DriftAlert]:
        alerts = list(self._alerts)
        if clear:
            self._alerts.clear()
        return alerts
