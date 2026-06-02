from src.core.learning_intelligence.models import LearnerSnapshot
from src.core.learning_intelligence.readiness.models import (
    ExamReadinessProfile,
    ForgettingRisk,
    StabilityScore,
)
from src.core.learning_intelligence.readiness.models.intervention import (
    Intervention,
)


class InterventionPlanner:
    def plan(
        self,
        snapshot: LearnerSnapshot,
        readiness_profile: ExamReadinessProfile,
        forgetting_risks: dict[str, ForgettingRisk],
        stabilities: dict[str, StabilityScore],
    ) -> list[Intervention]:
        interventions: list[Intervention] = []
        if not readiness_profile.topic_readiness:
            return interventions

        risk_topic_set = set(readiness_profile.risk_topics)
        misconceptions_by_topic: dict[str, bool] = {}
        for mc in snapshot.misconceptions:
            misconceptions_by_topic[mc.topic] = True

        readiness_by_topic = {
            tr.topic: tr.readiness_score
            for tr in readiness_profile.topic_readiness
        }

        all_topics = set(readiness_by_topic.keys())

        for topic in all_topics:
            readiness_score = readiness_by_topic.get(topic, 50.0)
            forgetting_risk = 0.3
            stability = 0.5

            if topic in forgetting_risks:
                forgetting_risk = forgetting_risks[topic].forgetting_risk
            if topic in stabilities:
                stability = stabilities[topic].stability_score

            is_risk_topic = topic in risk_topic_set
            has_misconception = misconceptions_by_topic.get(topic, False)
            high_forgetting = forgetting_risk > 0.6
            low_stability = stability < 0.4

            priority = (
                (1.0 - readiness_score / 100.0) * 0.5
                + forgetting_risk * 0.3
                + (1.0 - stability) * 0.2
            )

            if is_risk_topic and has_misconception:
                impact = max(0.0, 100.0 - readiness_score) * (
                    readiness_profile.confidence_score * 0.5 + 0.5
                )
                interventions.append(
                    Intervention(
                        topic=topic,
                        priority=priority,
                        action_type="REVISE_MISCONCEPTION",
                        estimated_impact=round(impact, 1),
                        reason=(
                            f"High-risk topic with persistent misconception"
                            f" — revise {topic} to improve exam readiness"
                        ),
                    )
                )
            elif is_risk_topic:
                impact = max(0.0, 100.0 - readiness_score) * (
                    readiness_profile.confidence_score * 0.5 + 0.5
                )
                interventions.append(
                    Intervention(
                        topic=topic,
                        priority=priority,
                        action_type="REVIEW_TOPIC",
                        estimated_impact=round(impact, 1),
                        reason=f"High-risk topic — review {topic} to improve exam readiness",
                    )
                )
            elif low_stability:
                impact = max(0.0, 100.0 - readiness_score) * (
                    readiness_profile.confidence_score * 0.5 + 0.5
                )
                interventions.append(
                    Intervention(
                        topic=topic,
                        priority=priority,
                        action_type="REVIEW_TOPIC",
                        estimated_impact=round(impact, 1),
                        reason=f"Unstable mastery — reinforce {topic} to prevent regression",
                    )
                )
            elif high_forgetting:
                impact = max(0.0, 100.0 - readiness_score) * (
                    readiness_profile.confidence_score * 0.5 + 0.5
                )
                interventions.append(
                    Intervention(
                        topic=topic,
                        priority=priority,
                        action_type="REVIEW_TOPIC",
                        estimated_impact=round(impact, 1),
                        reason=f"High forgetting risk — schedule a review of {topic}",
                    )
                )

        interventions.sort(key=lambda i: i.priority, reverse=True)
        return interventions
