from src.evaluation.hallucination.detector import HallucinationDetector
from src.evaluation.hallucination.models import DetectionMode
from src.graph.state import AgentState


class HallucinationNode:
    def __init__(self, mode: DetectionMode = DetectionMode.FULL, router=None):
        self.detector = HallucinationDetector(mode=mode, router=router)

    async def __call__(self, state: AgentState) -> AgentState:
        report = await self.detector.analyze(
            response_text=state.grounded_response or state.draft or "",
            citation_map=state.citation_map,
            evidence_items=state.evidence_items,
        )

        state.hallucination_rate = report.hallucination_rate
        state.hallucination_report = report.model_dump()

        return state
