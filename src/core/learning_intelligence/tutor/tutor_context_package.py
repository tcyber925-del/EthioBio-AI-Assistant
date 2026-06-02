"""TutorContextPackage — bundles learner snapshot, profile, recommendations, and strategy."""

from dataclasses import dataclass, field

from src.core.learning_intelligence.models import LearnerSnapshot, MisconceptionSummary
from src.core.learning_intelligence.recommendation.models import LearningRecommendation


@dataclass
class TutorContextPackage:
    learner_snapshot: LearnerSnapshot
    profile_block: str
    difficulty_level: str
    known_misconceptions: list[MisconceptionSummary] = field(default_factory=list)
    top_recommendations: list[LearningRecommendation] = field(default_factory=list)
    selected_strategy: str = ""
    formatted_block: str = ""
