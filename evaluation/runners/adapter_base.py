from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from evaluation.models import ComponentType, EvaluationResult


class EvalAdapter(ABC):
    """Base class for component evaluation adapters.

    Each adapter knows how to:
    1. Load its benchmark from the dataset entry
    2. Execute the component (or call its mocked interface)
    3. Score the output
    4. Return an EvaluationResult
    """

    component_type: ComponentType

    @abstractmethod
    async def execute(self, benchmark: Any, mock_llm: Any | None = None) -> EvaluationResult:
        """Run the component against a single benchmark entry."""
