import time
from dataclasses import dataclass
from threading import Lock

import structlog

from src.config import settings

logger = structlog.get_logger()


@dataclass
class Counter:
    name: str
    _value: int = 0

    def inc(self, labels: dict[str, str] | None = None) -> None:
        self._value += 1
        merged = labels or {}
        logger.debug(
            "observability.metric",
            metric=self.name,
            type="counter",
            value=self._value,
            **merged,
        )


@dataclass
class Gauge:
    name: str
    _value: float = 0.0

    def set(self, value: float, labels: dict[str, str] | None = None) -> None:
        self._value = value
        merged = labels or {}
        logger.debug(
            "observability.metric",
            metric=self.name,
            type="gauge",
            value=self._value,
            **merged,
        )


@dataclass
class Histogram:
    name: str
    _value: float = 0.0

    def observe(self, value: float, labels: dict[str, str] | None = None) -> None:
        self._value = value
        merged = labels or {}
        logger.debug(
            "observability.metric",
            metric=self.name,
            type="histogram",
            value=value,
            **merged,
        )


class MetricsRegistry:
    def __init__(self):
        self._lock = Lock()
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}

    def counter(self, name: str) -> Counter:
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name=name)
            return self._counters[name]

    def gauge(self, name: str) -> Gauge:
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name=name)
            return self._gauges[name]

    def histogram(self, name: str) -> Histogram:
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(name=name)
            return self._histograms[name]

    def to_dict(self) -> dict:
        with self._lock:
            return {
                **{k: v._value for k, v in self._counters.items()},
                **{k: v._value for k, v in self._gauges.items()},
                **{k: v._value for k, v in self._histograms.items()},
            }

    def prometheus_text(self) -> str:
        lines: list[str] = []
        with self._lock:
            for name, c in self._counters.items():
                safe = name.replace(".", "_").replace("-", "_")
                lines.append(f"# HELP {safe} Counter metric")
                lines.append(f"# TYPE {safe} counter")
                lines.append(f"{safe} {c._value}")
            for name, g in self._gauges.items():
                safe = name.replace(".", "_").replace("-", "_")
                lines.append(f"# HELP {safe} Gauge metric")
                lines.append(f"# TYPE {safe} gauge")
                lines.append(f"{safe} {g._value}")
            for name, h in self._histograms.items():
                safe = name.replace(".", "_").replace("-", "_")
                lines.append(f"# HELP {safe} Histogram metric")
                lines.append(f"# TYPE {safe} histogram")
                lines.append(f"{safe} {h._value}")
        return "\n".join(lines) + "\n"


registry = MetricsRegistry() if settings.observability_metrics_enabled else None


def _r():
    return registry if registry else _NoopRegistry()


class _NoopRegistry:
    class _Noop:
        def inc(self, *a, **kw): pass
        def set(self, *a, **kw): pass
        def observe(self, *a, **kw): pass

    def counter(self, _name): return self._Noop()
    def gauge(self, _name): return self._Noop()
    def histogram(self, _name): return self._Noop()


def inc_counter(name: str, labels: dict | None = None) -> None:
    _r().counter(name).inc(labels)


def set_gauge(name: str, value: float, labels: dict | None = None) -> None:
    _r().gauge(name).set(value, labels)


def observe_histogram(name: str, value: float, labels: dict | None = None) -> None:
    _r().histogram(name).observe(value, labels)


class Timer:
    """Context manager — records duration to histogram."""

    def __init__(self, metric_name: str, labels: dict | None = None):
        self.metric_name = metric_name
        self.labels = labels or {}
        self.start: float = 0.0

    def __enter__(self):
        self.start = time.monotonic()
        return self

    def __exit__(self, *args):
        duration = time.monotonic() - self.start
        observe_histogram(self.metric_name, duration, self.labels)
