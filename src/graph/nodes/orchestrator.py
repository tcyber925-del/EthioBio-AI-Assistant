"""Orchestrator node — classifies intent and routes to the right agent.

Hybrid routing: LLM intent classification + heuristic complexity scoring.
requires_planning is derived from complexity score (>=0.7), memory signals,
multi-hop signals, and cross-session signals.
"""

import json
import re

from src.graph.state import AgentState
from src.llm.router import ModelRouter
from src.schemas.streaming import TokenChunk

# ============================================================
# Heuristic Patterns (Phase 0 — fast path classification)
# ============================================================

# Intents that should never invoke the Planner
HARD_EXCLUDED_INTENTS = frozenset(
    {"translation", "grammar", "formatting", "small_talk", "conversation"}
)

# Patterns that suggest the query is simple (no planning needed)
SIMPLE_PATTERNS = [
    r"^what is\b",
    r"^define\b",
    r"^translate\b",
    r"^generate a quiz\b",
    r"^generate quiz\b",
    r"^create quiz\b",
    r"^hello\b",
    r"^hi\b",
    r"^hey\b",
    r"^thank",
    r"^goodbye\b",
    r"^bye\b",
]

# Patterns that suggest the query is complex (planning likely needed)
COMPLEX_PATTERNS = [
    r"\bwhy do i\b",
    r"\bwhy did i\b",
    r"\bwhy do i keep\b",
    r"\bacross previous\b",
    r"\bhistorically\b",
    r"\bover time\b",
    r"\bwhat patterns\b",
    r"\bhow are.*related\b",
    r"\bwhich topics.*struggle",
    r"\bwhich.*weakness",
    r"\bmisconception.*still\b",
    r"\blearning progress\b",
    r"\brelate\b.*\bto\b",
    r"\banalyze my\b",
    r"\bmy weakness",
    r"\bmy misconception",
    r"\bmy learning history",
    r"\bmy progress\b",
    r"\bconnect.*to\b",
]

# Keywords that indicate personalization (memory retrieval needed)
PERSONALIZATION_KEYWORDS = [
    "my ",
    "i ",
    "previously",
    "before",
    "struggled",
    "weakness",
    "misconception",
    "confusing",
    "confused",
    "forget",
    "forgot",
    "keep making",
    "keep getting",
    "always",
    "never understand",
]


def classify_complexity_heuristic(user_message: str) -> tuple[str, float]:
    """Fast heuristic classification of query complexity.

    Returns: (complexity_label, complexity_score)
    """
    msg_lower = user_message.lower()

    # Check simple patterns first
    for pattern in SIMPLE_PATTERNS:
        if re.search(pattern, msg_lower):
            return "LOW", 0.2

    # Check complex patterns
    for pattern in COMPLEX_PATTERNS:
        if re.search(pattern, msg_lower):
            return "HIGH", 0.85

    # Default: medium complexity, needs LLM to resolve
    return "MEDIUM", 0.5


def detect_requires_memory(user_message: str) -> bool:
    """Check if the query references personal learning history."""
    msg_lower = user_message.lower()
    return any(kw in msg_lower for kw in PERSONALIZATION_KEYWORDS)


def detect_requires_multi_hop(user_message: str) -> bool:
    """Check if the query requires multi-hop reasoning."""
    msg_lower = user_message.lower()
    multi_hop_signals = [
        r"\brelate\b",
        r"\bhow does.*affect\b",
        r"\bhow does.*relate\b",
        r"\bconnect\b",
        r"\bexplain why\b",
        r"\banalyze\b",
    ]
    return any(re.search(p, msg_lower) for p in multi_hop_signals)


def detect_requires_cross_session(user_message: str) -> bool:
    """Check if the query requires cross-session analysis."""
    msg_lower = user_message.lower()
    cross_session_signals = [
        r"\bacross previous\b",
        r"\bover time\b",
        r"\bhistorically\b",
        r"\bwhat patterns\b",
        r"\btrend\b",
        r"\bover the last\b",
        r"\bin past\b",
        r"\bpreviously\b",
    ]
    return any(re.search(p, msg_lower) for p in cross_session_signals)


    def _push_status(self, state: AgentState, message: str):
        if state.token_queue:
            state.token_queue.put_nowait(TokenChunk(delta=message, node="orchestrator", status=True))


class OrchestratorNode:
    def __init__(self, router: ModelRouter):
        self.router = router

    async def __call__(self, state: AgentState) -> AgentState:
        self._push_status(state, "Analyzing your question...")
        prompt = f"""You are an intent classifier for an Ethiopian biology education assistant.
Classify the user's message into exactly one of these intents:
- "tutor": biology question, concept explanation, homework help
- "quiz": wants a quiz, test, practice questions
- "lesson_plan": wants a lesson plan created
- "progress": wants to check progress or performance
- "translation": wants content translated to/from Amharic
- "admin": administrative or system question
- "general": greeting, chitchat, or unclear

User message: "{state.user_message}"

Respond with ONLY a JSON object: {{"intent": "tutor", "confidence": 0.95}}"""

        messages = [
            {"role": "system", "content": "You are a precise intent classifier."},
            {"role": "user", "content": prompt},
        ]

        result = await self.router.route(
            messages,
            request_type="intent_classification",
            temperature=0.1,
            max_tokens=200,
        )

        try:
            content = result["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            parsed = json.loads(content)
            state.intent = parsed.get("intent", "tutor")
            state.intent_confidence = parsed.get("confidence", 0.5)
        except (json.JSONDecodeError, KeyError):
            state.intent = "tutor"
            state.intent_confidence = 0.5

        # ============================================================
        # Hybrid Complexity Routing
        # ============================================================

        # Step 1: Hard intent exclusion
        if state.intent in HARD_EXCLUDED_INTENTS:
            state.requires_planning = False
            state.complexity_score = 0.0
            return state

        # Step 2: Heuristic complexity classification
        heuristic_label, heuristic_score = classify_complexity_heuristic(state.user_message)

        # Step 3: Feature extraction
        requires_memory = detect_requires_memory(state.user_message)
        requires_multi_hop = detect_requires_multi_hop(state.user_message)
        requires_cross_session = detect_requires_cross_session(state.user_message)

        # Step 4: Routing decision
        state.requires_planning = (
            heuristic_score >= 0.7
            or requires_memory
            or requires_multi_hop
            or requires_cross_session
        )
        state.complexity_score = heuristic_score

        return state


def needs_retrieval(state: AgentState) -> str:
    if state.intent in ("tutor", "quiz", "lesson_plan"):
        return "retrieve"
    return "skip_retrieval"
