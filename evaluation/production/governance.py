from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


PRODUCTION_GOVERNANCE_THRESHOLDS = {
    "requires_trace_id": True,
    "requires_evidence_provenance": True,
    "requires_audit_logging": True,
    "requires_structured_logging": True,
    "requires_source_attribution": True,
}


def check_trace_id_flow() -> dict[str, Any]:
    """Verify trace IDs flow through the pipeline."""
    try:
        from src.graph.state import AgentState

        has_trace = "trace_id" in AgentState.__dataclass_fields__ if hasattr(AgentState, "__dataclass_fields__") else False
        return {
            "check": "trace_id_in_state",
            "passed": has_trace,
            "detail": "AgentState has trace_id field" if has_trace else "No trace_id in AgentState",
        }
    except (ImportError, AttributeError):
        return {"check": "trace_id_in_state", "passed": False, "detail": "AgentState not accessible"}


def check_evidence_provenance() -> dict[str, Any]:
    """Verify EvidenceGraph captures full provenance for each chunk."""
    try:
        from src.core.evidence.graph import EvidenceGraph
        from src.database.models import EvidenceRecord

        has_store = hasattr(EvidenceGraph, "store_evidence") or hasattr(EvidenceGraph, "add_evidence")
        has_record = isinstance(EvidenceRecord.__tablename__, str) if hasattr(EvidenceRecord, "__tablename__") else False
        return {
            "check": "evidence_provenance",
            "passed": has_store and has_record,
            "detail": "EvidenceGraph with EvidenceRecord persistence" if has_store and has_record else "EvidenceGraph or EvidenceRecord incomplete",
        }
    except ImportError:
        return {"check": "evidence_provenance", "passed": False, "detail": "EvidenceGraph not found"}


def check_audit_logging() -> dict[str, Any]:
    """Verify audit trail mechanisms exist."""
    try:
        from src.core.monitoring import PipelineMonitor

        has_trace = hasattr(PipelineMonitor, "trace_node") or hasattr(PipelineMonitor, "log_node")
        return {
            "check": "audit_logging",
            "passed": has_trace,
            "detail": "PipelineMonitor with node tracing" if has_trace else "PipelineMonitor exists but no tracing methods",
        }
    except ImportError:
        return {"check": "audit_logging", "passed": False, "detail": "PipelineMonitor not found"}


def check_structured_logging() -> dict[str, Any]:
    """Verify structured logging is configured."""
    import logging as _logging

    root = _logging.getLogger()
    has_handlers = len(root.handlers) > 0
    return {
        "check": "structured_logging",
        "passed": has_handlers,
        "detail": "Logging handlers configured" if has_handlers else "No root logging handlers",
    }


def check_source_attribution() -> dict[str, Any]:
    """Verify source attribution exists in the evidence pipeline."""
    try:
        from src.database.models import EvidenceRecord

        cols = [c.name for c in EvidenceRecord.__table__.columns] if hasattr(EvidenceRecord, "__table__") else []
        has_source_type = "source_type" in cols
        has_source_name = "source_name" in cols
        return {
            "check": "source_attribution",
            "passed": has_source_type and has_source_name,
            "detail": "EvidenceRecord has source_type and source_name columns" if has_source_type and has_source_name else "EvidenceRecord missing source attribution columns",
        }
    except (ImportError, AttributeError):
        return {"check": "source_attribution", "passed": False, "detail": "EvidenceRecord not accessible"}


def run_governance_checks() -> dict[str, Any]:
    """Run all governance certification checks."""
    checks = [
        check_trace_id_flow(),
        check_evidence_provenance(),
        check_audit_logging(),
        check_structured_logging(),
        check_source_attribution(),
    ]

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    score = passed / total if total > 0 else 0.0

    return {
        "score": round(score, 3),
        "passed": passed,
        "total": total,
        "checks": checks,
        "failures": [c["check"] for c in checks if not c["passed"]],
    }
