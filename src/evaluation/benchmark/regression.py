import json

DEFAULT_TOLERANCE = 0.15


class RegressionDetector:
    def __init__(self, baselines: dict[str, dict]):
        self.baselines = baselines

    @classmethod
    def from_json(cls, json_str: str) -> "RegressionDetector":
        data = json.loads(json_str)
        scenarios = data.get("scenarios", data)  # accept flat or nested format
        return cls(scenarios)

    def check(self, scenario_id: str, metrics: dict) -> list[str]:
        baseline = self.baselines.get(scenario_id)
        if not baseline:
            return []

        issues: list[str] = []

        min_g = baseline.get("min_groundedness")
        if min_g is not None:
            actual = metrics.get("groundedness_score", 0.0)
            if actual < min_g:
                issues.append(f"groundedness {actual:.3f} < min {min_g:.3f}")

        max_h = baseline.get("max_hallucination_rate")
        if max_h is not None:
            actual = metrics.get("hallucination_rate", 0.0)
            if actual > max_h:
                issues.append(f"hallucination_rate {actual:.3f} > max {max_h:.3f}")

        min_c = baseline.get("min_coverage_score")
        if min_c is not None:
            actual = metrics.get("coverage_score", 0.0)
            if actual < min_c:
                issues.append(f"coverage {actual:.3f} < min {min_c:.3f}")

        max_d = baseline.get("max_duration_ms")
        if max_d is not None:
            actual = metrics.get("duration_ms", 0.0)
            if actual > max_d:
                issues.append(f"duration {actual:.0f}ms > max {max_d:.0f}ms")

        return issues

    @staticmethod
    def generate_baseline(
        metrics: dict,
        tolerance: float = DEFAULT_TOLERANCE,
    ) -> dict:
        groundedness = metrics.get("groundedness_score")
        hallucination = metrics.get("hallucination_rate")
        coverage = metrics.get("coverage_score")
        duration = metrics.get("duration_ms")

        baseline: dict[str, float] = {}
        if groundedness is not None:
            baseline["min_groundedness"] = round(groundedness * (1 - tolerance), 3)
        if hallucination is not None:
            baseline["max_hallucination_rate"] = round(hallucination * (1 + tolerance), 3)
        if coverage is not None:
            baseline["min_coverage_score"] = round(coverage * (1 - tolerance), 3)
        if duration is not None:
            baseline["max_duration_ms"] = round(duration * (1 + tolerance), 1)

        return baseline
