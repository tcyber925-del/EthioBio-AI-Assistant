import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import structlog

from src.config import settings

logger = structlog.get_logger()

SCORE_HISTORY_PATH = Path(".score_history.json")


@dataclass
class WeeklyStats:
    week: str
    avg_score: float
    n: int


@dataclass
class ScoreHistory:
    dimension: str
    weeks: list[WeeklyStats] = field(default_factory=list)


class DriftDetector:
    def __init__(self):
        self._history: dict[str, ScoreHistory] = {}
        self._threshold = settings.eval_drift_threshold
        self._load()

    def _load(self) -> None:
        if SCORE_HISTORY_PATH.exists():
            try:
                data = json.loads(SCORE_HISTORY_PATH.read_text())
                for dim, stats in data.items():
                    self._history[dim] = ScoreHistory(
                        dimension=dim,
                        weeks=[WeeklyStats(**w) for w in stats.get("weeks", [])],
                    )
            except (json.JSONDecodeError, Exception):
                pass

    def _save(self) -> None:
        data = {}
        for dim, history in self._history.items():
            weeks = [{"week": w.week, "avg_score": w.avg_score, "n": w.n} for w in history.weeks]
            data[dim] = {"weeks": weeks}
        SCORE_HISTORY_PATH.write_text(json.dumps(data, indent=2))

    def record_week(self, dimension: str, avg_score: float, n: int) -> None:
        if dimension not in self._history:
            self._history[dimension] = ScoreHistory(dimension=dimension)
        week = time.strftime("%Y-W%W")
        self._history[dimension].weeks.append(WeeklyStats(week=week, avg_score=avg_score, n=n))
        self._save()

    def get_baseline(self, dimension: str) -> Optional[float]:
        history = self._history.get(dimension)
        if not history:
            return None
        recent = [w for w in history.weeks[-4:] if w.n >= 10]
        if not recent:
            return None
        return sum(w.avg_score * w.n for w in recent) / sum(w.n for w in recent)

    def check_drift(self, dimension: str, current_score: float) -> Optional[float]:
        baseline = self.get_baseline(dimension)
        if baseline is None:
            return None
        drift = abs(current_score - baseline)
        if drift > self._threshold:
            logger.warning(
                "eval_drift_detected",
                dimension=dimension,
                current=current_score,
                baseline=baseline,
                drift=drift,
                threshold=self._threshold,
            )
        return drift


drift_detector = DriftDetector()
