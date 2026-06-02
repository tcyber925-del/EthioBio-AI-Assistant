from src.core.learning_intelligence.models import LearnerSnapshot
from src.core.learning_intelligence.readiness.models.mastery_stability import (
    StabilityScore,
)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class MasteryStabilityPredictor:
    def predict_stability(
        self,
        snapshot: LearnerSnapshot,
    ) -> dict[str, StabilityScore]:
        results: dict[str, StabilityScore] = {}
        mastery = snapshot.mastery_by_topic
        if not mastery:
            return results

        reviews_by_topic = {r.topic: r for r in snapshot.due_reviews}
        plans_by_topic = {p.topic: p for p in snapshot.active_recovery_plans}

        for topic, mastery_data in mastery.items():
            mastery_score = float(mastery_data.get("average_score", 0))

            ability_data = snapshot.ability_by_topic.get(topic, {})
            ability_uncertainty = float(ability_data.get("uncertainty", 3.0))

            review = reviews_by_topic.get(topic)
            review_count = 1 if review is not None else 0

            recovery_progress = 0.0
            plan = plans_by_topic.get(topic)
            if plan is not None and plan.total_tasks > 0:
                recovery_progress = plan.progress_pct / 100.0

            mastery_component = mastery_score / 100.0 * 0.4
            uncertainty_component = (
                clamp(1.0 - ability_uncertainty / 3.0, 0.0, 1.0) * 0.3
            )
            review_component = clamp(review_count / 10.0, 0.0, 1.0) * 0.2
            recovery_component = recovery_progress * 0.1

            stability = clamp(
                mastery_component
                + uncertainty_component
                + review_component
                + recovery_component,
                0.0,
                1.0,
            )

            if stability >= 0.7:
                band = "Stable"
            elif stability >= 0.4:
                band = "Moderate"
            else:
                band = "Volatile"

            results[topic] = StabilityScore(
                topic=topic,
                stability_score=stability,
                stability_band=band,
            )

        return results
