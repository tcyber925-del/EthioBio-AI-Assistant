import re
from dataclasses import dataclass, field

from src.config import settings
from src.observability.guardrail_instrumentation import observe_guardrail

ETHIOBIO_TOPICS = frozenset(
    {
        "biology",
        "cell",
        "genetics",
        "evolution",
        "ecology",
        "human body",
        "plant",
        "animal",
        "microbiology",
        "photosynthesis",
        "respiration",
        "digestive",
        "circulatory",
        "nervous",
        "skeletal",
        "muscular",
        "excretory",
        "endocrine",
        "immune",
        "reproductive",
        "dna",
        "rna",
        "protein",
        "enzyme",
        "chromosome",
        "bacteria",
        "virus",
        "fungus",
        "protist",
        "ecosystem",
        "food chain",
        "food web",
        "biome",
        "habitat",
        "classification",
        "taxonomy",
        "species",
        "genus",
        "mitosis",
        "meiosis",
        "cell division",
        "atom",
        "molecule",
        "chemical",
        "element",
        "compound",
        "force",
        "motion",
        "energy",
        "electricity",
        "magnetism",
        "scientific method",
        "experiment",
        "hypothesis",
    }
)


@dataclass
class TopicEnforcementResult:
    on_topic: bool
    off_topic_segments: list[str] = field(default_factory=list)
    confidence: float = 1.0


OFF_TOPIC_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"\b(politics|election|candidate|president|vote|democrat|republican)\b", re.IGNORECASE
    ),
    re.compile(r"\b(religion|god|bible|quran|prayer|worship)\b", re.IGNORECASE),
    re.compile(r"\b(gambling|casino|bet|lottery)\b", re.IGNORECASE),
    re.compile(r"\b(adult|porn|nsfw)\b", re.IGNORECASE),
    re.compile(r"\b(investment|stock|crypto|bitcoin|trading)\b", re.IGNORECASE),
]


class TopicEnforcer:
    def __init__(self):
        self._enabled = settings.output_topic_enforcement_enabled

    @observe_guardrail(module="topic_enforcer", guardrail_type="output")
    def check(self, text: str, topic: str | None = None) -> TopicEnforcementResult:
        if not self._enabled:
            return TopicEnforcementResult(on_topic=True)

        text_lower = text.lower()
        off_topic_segments = []

        for pattern in OFF_TOPIC_PATTERNS:
            matches = pattern.findall(text_lower)
            if matches:
                off_topic_segments.append(f"Off-topic content detected: {', '.join(set(matches))}")

        if off_topic_segments:
            return TopicEnforcementResult(
                on_topic=False,
                off_topic_segments=off_topic_segments,
                confidence=0.0,
            )

        if topic:
            topic_lower = topic.lower()
            topic_words = topic_lower.split()
            if not any(tw in text_lower for tw in topic_words if len(tw) > 3):
                if not any(kt in text_lower for kt in ETHIOBIO_TOPICS):
                    return TopicEnforcementResult(
                        on_topic=False,
                        off_topic_segments=["Response does not align with the specified topic"],
                        confidence=0.3,
                    )

        return TopicEnforcementResult(on_topic=True)
