from src.core.learning_intelligence.recommendation.models import (
    LearningRecommendation,
)


class PriorityCalculator:
    RAW_WEIGHTS: dict[str, int] = {
        "critical": 40,
        "moderate": 25,
        "mild": 10,
        "good": 0,
        "overdue_1_3": 10,
        "overdue_4_7": 20,
        "overdue_8plus": 30,
        "misconception": 20,
        "active_plan": 15,
        "near_completion": 10,
        "streak_risk": 10,
        "inactive": 15,
    }

    MAX_POSSIBLE_SCORE: int = 120

    @staticmethod
    def normalize(raw: float) -> float:
        normalized = raw / PriorityCalculator.MAX_POSSIBLE_SCORE
        return max(0.0, min(1.0, normalized))

    @staticmethod
    def deduplicate(
        recommendations: list[LearningRecommendation],
    ) -> list[LearningRecommendation]:
        seen: dict[tuple, LearningRecommendation] = {}
        for rec in recommendations:
            key = (rec.action_type, rec.topic)
            if key not in seen or rec.priority_score > seen[key].priority_score:
                seen[key] = rec
        return list(seen.values())

    @staticmethod
    def score_and_sort(
        recommendations: list[LearningRecommendation],
    ) -> list[LearningRecommendation]:
        normalized = []
        for rec in recommendations:
            rec.priority_score = PriorityCalculator.normalize(rec.priority_score)
            normalized.append(rec)
        deduped = PriorityCalculator.deduplicate(normalized)
        deduped.sort(key=lambda r: r.priority_score, reverse=True)
        return deduped[:5]
