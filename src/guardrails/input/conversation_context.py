import time
from dataclasses import dataclass, field
from typing import Optional

import structlog

from src.observability.guardrail_instrumentation import observe_guardrail

logger = structlog.get_logger()

TURN_TTL = 3600
MAX_RECENT_TURNS = 10

MULTI_TURN_PATTERNS: list[tuple[set[str], float]] = [
    ({"ignore", "previous", "instructions"}, 0.6),
    ({"forget", "context", "history"}, 0.5),
    ({"new", "role", "you", "are"}, 0.6),
    ({"act", "as", "if", "you"}, 0.6),
    ({"pretend", "now"}, 0.5),
    ({"from", "now", "on", "you"}, 0.5),
    ({"system", "prompt"}, 0.6),
    ({"override", "previous"}, 0.6),
    ({"ignore", "safety"}, 0.8),
    ({"disable", "filter"}, 0.8),
    ({"no", "restrictions"}, 0.7),
]


@dataclass
class ConversationTurn:
    timestamp: float
    content: str


@dataclass
class ConversationContext:
    user_id: str
    turns: list[ConversationTurn] = field(default_factory=list)
    injection_flag: bool = False
    injection_confidence: float = 0.0

    def add_turn(self, content: str):
        now = time.time()
        self.turns.append(ConversationTurn(timestamp=now, content=content))
        cutoff = now - TURN_TTL
        self.turns = [t for t in self.turns if t.timestamp >= cutoff]
        if len(self.turns) > MAX_RECENT_TURNS:
            self.turns = self.turns[-MAX_RECENT_TURNS:]

    @observe_guardrail(module="multiturn_attack", guardrail_type="input")
    def check_multiturn_attack(self, current_message: str) -> float:
        min_recent = 2
        if len(self.turns) < min_recent:
            return 0.0

        recent = [t.content for t in self.turns[-min_recent:]]
        combined = " ".join(recent)

        current_lower = current_message.lower()
        combined_lower = combined.lower()

        max_confidence = 0.0
        for pattern, weight in MULTI_TURN_PATTERNS:
            matched_in_current = sum(1 for w in pattern if w in current_lower)
            matched_in_history = sum(1 for w in pattern if w in combined_lower)
            if matched_in_current >= 2 and matched_in_history >= 2:
                if weight > max_confidence:
                    max_confidence = weight

        return max_confidence


class ConversationTracker:
    def __init__(self):
        self._sessions: dict[str, ConversationContext] = {}

    def get_or_create(self, user_id: str) -> ConversationContext:
        if user_id not in self._sessions:
            self._sessions[user_id] = ConversationContext(user_id=user_id)
        return self._sessions[user_id]

    def get(self, user_id: str) -> Optional[ConversationContext]:
        return self._sessions.get(user_id)
