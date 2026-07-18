from src.core.learning_intelligence.models import LearnerSnapshot
from src.core.learning_intelligence.readiness.models.forgetting_risk import (
    ForgettingRisk,
)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class ForgettingRiskPredictor:
    def predict_forgetting(
        self,
        snapshot: LearnerSnapshot,
    ) -> dict[str, ForgettingRisk]:
        results: dict[str, ForgettingRisk] = {}
        mastery = snapshot.mastery_by_topic
        if not mastery:
            return results

        reviews_by_topic = {r.topic: r for r in snapshot.due_reviews}
        plans_by_topic = {p.topic: p for p in snapshot.active_recovery_plans}

        for topic, mastery_data in mastery.items():
            mastery_score = float(mastery_data.get("average_score", 50))
            review = reviews_by_topic.get(topic)
            factors: list[str] = []

            if review is not None:
                days_overdue = review.days_overdue
                base_risk = min(days_overdue / 30.0, 1.0)
                ease_factor = 2.5
                review_count = 1
                base_risk = base_risk * (2.5 - ease_factor) / 1.2
                base_risk = base_risk * max(0.0, 1.0 - review_count * 0.1)
                base_risk = base_risk * (1.0 - mastery_score / 100.0 * 0.5)
                forgetting_risk = clamp(base_risk, 0.01, 0.99)
                if days_overdue > 0:
                    factors.append("overdue_review")
                factors.append("has_review_data")
                results[topic] = ForgettingRisk(
                    topic=topic,
                    forgetting_risk=forgetting_risk,
                    days_overdue=days_overdue,
                    ease_factor=ease_factor,
                    review_count=review_count,
                    contributing_factors=factors,
                )
            else:
                recovery_progress = 0.0
                plan = plans_by_topic.get(topic)
                if plan is not None and plan.total_tasks > 0:
                    recovery_progress = plan.progress_pct / 100.0
                base_risk = max(0.15, 1.0 - mastery_score / 100.0 * 0.7)
                base_risk = base_risk * (1.0 - recovery_progress * 0.3)
                forgetting_risk = clamp(base_risk, 0.01, 0.99)
                factors.append("no_review_data")
                if plan is not None:
                    factors.append("has_recovery_plan")
                results[topic] = ForgettingRisk(
                    topic=topic,
                    forgetting_risk=forgetting_risk,
                    contributing_factors=factors,
                )

        return results
