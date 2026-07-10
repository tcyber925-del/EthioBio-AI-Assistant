from datetime import datetime, timezone

from src.core.learning_intelligence.models import LearnerSnapshot
from src.core.learning_intelligence.readiness.models import (
    ExamReadinessProfile,
    ForgettingRisk,
    StabilityScore,
)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class ProjectedScoreCalculator:
    def calculate(
        self,
        readiness_profile: ExamReadinessProfile,
        forgetting_risks: dict[str, ForgettingRisk],
        stabilities: dict[str, StabilityScore],
        snapshot: LearnerSnapshot,
    ) -> tuple[float, float]:
        if not readiness_profile.topic_readiness:
            return (0.0, 0.5)

        overall_readiness = readiness_profile.overall_readiness

        ability_scores = [
            float(d.get("ability_score", 0)) for d in snapshot.ability_by_topic.values()
        ]
        avg_ability = sum(ability_scores) / len(ability_scores) if ability_scores else 0.0

        stability_values = [s.stability_score for s in stabilities.values()]
        avg_stability = sum(stability_values) / len(stability_values) if stability_values else 0.0

        forgetting_values = [r.forgetting_risk for r in forgetting_risks.values()]
        avg_forgetting = (
            sum(forgetting_values) / len(forgetting_values) if forgetting_values else 0.0
        )

        projected = (
            overall_readiness * 0.40
            + clamp(avg_ability, -3.0, 3.0) * 100.0 * 0.25
            + avg_stability * 100.0 * 0.20
            + (1.0 - avg_forgetting) * 100.0 * 0.15
        )
        projected = clamp(projected, 0.0, 100.0)

        confidence = 1.0
        for topic, mastery_data in snapshot.mastery_by_topic.items():
            attempt_count = int(mastery_data.get("attempt_count", 0))
            if attempt_count < 3:
                confidence -= 0.1

            ability_data = snapshot.ability_by_topic.get(topic, {})
            uncertainty = float(ability_data.get("uncertainty", 0.0))
            if uncertainty > 2.0:
                confidence -= 0.1

        snapshot_age = datetime.now(timezone.utc) - snapshot.generated_at
        if snapshot_age.days >= 7:
            confidence -= 0.1

        confidence = clamp(confidence, 0.10, 1.00)

        return (projected, confidence)
