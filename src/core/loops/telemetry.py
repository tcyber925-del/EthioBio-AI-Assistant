"""Telemetry for the iterative retrieval loop."""


def record_loop_decision(state) -> dict:
    """Return loop metrics dict for PipelineMonitor."""
    return {
        "iteration": state.retrieval_iterations,
        "coverage": state.coverage_score,
        "sufficiency": getattr(state, "sufficiency_score", 0.0),
        "termination": state.termination_reason,
        "evidence_count": len(state.evidence_ids),
        "coverage_history": list(state.coverage_history),
    }
