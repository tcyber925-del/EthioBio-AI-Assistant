"""Learner Profile Builder — generates a learner-aware system prompt block from a LearnerSnapshot."""  # noqa: E501

from dataclasses import dataclass, field

from src.core.learning_intelligence.models import (
    LearnerSnapshot,
    MisconceptionSummary,
)


@dataclass
class BuildProfileResult:
    difficulty_level: str
    profile_block: str
    known_misconceptions: list[MisconceptionSummary] = field(default_factory=list)


class LearnerProfileBuilder:
    def build_profile(
        self,
        snapshot: LearnerSnapshot,
        current_topic: str | None = None,
        readiness_context: dict | None = None,
    ) -> BuildProfileResult:
        difficulty_level = self._determine_difficulty(snapshot)
        known_misconceptions = self._find_misconceptions(snapshot, current_topic)
        profile_block = self._format_profile_block(
            snapshot,
            difficulty_level,
            known_misconceptions,
            readiness_context=readiness_context,
            current_topic=current_topic,
        )
        return BuildProfileResult(
            difficulty_level=difficulty_level,
            profile_block=profile_block,
            known_misconceptions=known_misconceptions,
        )

    def _determine_difficulty(self, snapshot: LearnerSnapshot) -> str:
        confidence = snapshot.educational_memory.confidence
        has_critical = any(
            isinstance(m, dict) and m.get("severity") == "critical"
            for m in snapshot.mastery_by_topic.values()
        )
        has_moderate = any(
            isinstance(m, dict) and m.get("severity") == "moderate"
            for m in snapshot.mastery_by_topic.values()
        )

        abilities = self._extract_ability_scores(snapshot)
        any_below_minus_1 = any(a < -1.0 for a in abilities)
        any_below_0 = any(a < 0.0 for a in abilities)
        all_ge_0 = all(a >= 0.0 for a in abilities) if abilities else True
        all_gt_1 = all(a > 1.0 for a in abilities) if abilities else True

        no_weak_topics = len(snapshot.weak_topics) == 0

        if has_critical or (confidence is not None and confidence < 0.3) or any_below_minus_1:
            return "BEGINNER"

        if has_moderate or (confidence is not None and 0.3 <= confidence < 0.6) or any_below_0:
            return "DEVELOPING"

        if no_weak_topics and confidence is not None and confidence > 0.9 and all_gt_1:
            return "ADVANCED"

        if no_weak_topics and confidence is not None and confidence >= 0.6 and all_ge_0:
            return "PROFICIENT"

        return "BEGINNER"

    def _extract_ability_scores(self, snapshot: LearnerSnapshot) -> list[float]:
        scores: list[float] = []
        for v in snapshot.ability_by_topic.values():
            if isinstance(v, dict):
                score = v.get("ability_score")
                if isinstance(score, (int, float)):
                    scores.append(float(score))
        return scores

    def _find_misconceptions(
        self,
        snapshot: LearnerSnapshot,
        current_topic: str | None,
    ) -> list[MisconceptionSummary]:
        if not current_topic:
            return []
        return [m for m in snapshot.misconceptions if m.topic == current_topic and m.frequency >= 2]

    def _format_profile_block(
        self,
        snapshot: LearnerSnapshot,
        difficulty_level: str,
        known_misconceptions: list[MisconceptionSummary],
        readiness_context: dict | None = None,
        current_topic: str | None = None,
    ) -> str:
        lines = ["## Learner Profile"]

        if snapshot.weak_topics:
            lines.append(f"- Weak Topics: {', '.join(sorted(snapshot.weak_topics))}")
        if snapshot.strong_topics:
            lines.append(f"- Strong Topics: {', '.join(sorted(snapshot.strong_topics))}")
        if not snapshot.weak_topics and not snapshot.strong_topics:
            lines.append("- Topics: No mastery data available")

        lines.append(f"- Difficulty Level: {difficulty_level}")

        confidence = snapshot.educational_memory.confidence
        if confidence is not None:
            lines.append(f"- Confidence: {confidence:.2f}")
        if snapshot.ability_by_topic:
            ability_strs = []
            for topic, v in sorted(snapshot.ability_by_topic.items()):
                if isinstance(v, dict) and "ability_score" in v:
                    ability_strs.append(f"{topic}: {v['ability_score']:.2f}")
            if ability_strs:
                lines.append(f"- Ability Estimates: {', '.join(ability_strs)}")

        if known_misconceptions:
            lines.append("")
            lines.append("## Known Misconception")
            for m in known_misconceptions:
                lines.append(f"- Pattern: {m.pattern_type}")
                suffix = "s" if m.frequency > 1 else ""
                lines.append(f"  Frequency: {m.frequency} occurrence{suffix}")

        if readiness_context and current_topic:
            risk_topics = readiness_context.get("risk_topics", [])
            if current_topic in risk_topics:
                band = readiness_context.get("readiness_band", "Unknown")
                overall = readiness_context.get("overall_readiness", 0)
                lines.append("")
                lines.append("## Exam Readiness")
                lines.append(
                    f"- '{current_topic}' is a high-risk exam area"
                    f" (overall readiness: {overall:.0f}%, band: {band})."
                )
                lines.append("- Prioritise this topic during the session.")

        return "\n".join(lines)
