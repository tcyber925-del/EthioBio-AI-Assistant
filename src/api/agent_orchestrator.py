
from datetime import datetime

import structlog
from fastapi import APIRouter

from src.core.agent_orchestrator import AgentOrchestrator, build_orchestrator
from src.llm.router import ModelRouter
from src.retrieval.adapter import VectorStoreAdapter
from src.schemas.base import SchemaModel

logger = structlog.get_logger()
router = APIRouter(prefix="/agents", tags=["Agent Orchestrator"])


class ExecuteTaskRequest(SchemaModel):
    task: str
    context: dict = {}
    user_id: str | None = None
    preferred_agent: str | None = None


class ExecuteTaskResponse(SchemaModel):
    task_id: str = ""
    agent: str = ""
    result: dict = {}
    confidence: float = 0.0
    duration_ms: int = 0
    error: str | None = None


class AgentInfo(SchemaModel):
    name: str
    description: str
    capabilities: list[str] = []
    status: str = "idle"
    version: str = "1.0.0"


class CapabilityInfo(SchemaModel):
    name: str
    description: str
    agents: list[str] = []


class ReflectionInfo(SchemaModel):
    agent: str
    task: str
    verdict: str
    confidence: float
    duration_ms: int
    error: str | None = None
    timestamp: datetime | None = None


_orchestrator_instance: AgentOrchestrator | None = None

def _get_orchestrator() -> AgentOrchestrator:
    global _orchestrator_instance
    if _orchestrator_instance is None:
        router_llm = ModelRouter()
        adapter = VectorStoreAdapter()
        _orchestrator_instance = build_orchestrator(router_llm, adapter)
    return _orchestrator_instance


@router.post("/execute", response_model=ExecuteTaskResponse)
async def execute_agent_task(request: ExecuteTaskRequest):
    orchestrator = _get_orchestrator()
    result = await orchestrator.execute(
        task=request.task,
        context=request.context,
        user_id=request.user_id,
        preferred_agent=request.preferred_agent,
    )
    return ExecuteTaskResponse(**result)


@router.get("", response_model=list[AgentInfo])
async def list_agents():
    registry = _get_orchestrator().registry
    return [
        AgentInfo(
            name=reg.name,
            description=reg.description,
            capabilities=[c.name for c in reg.capabilities],
            status=reg.status.value,
            version=reg.version,
        )
        for reg in registry.list_agents()
    ]


@router.get("/capabilities", response_model=list[CapabilityInfo])
async def list_capabilities():
    registry = _get_orchestrator().registry
    cap_map: dict[str, list[str]] = {}
    for reg in registry.list_agents():
        for cap in reg.capabilities:
            if cap.name not in cap_map:
                cap_map[cap.name] = []
            cap_map[cap.name].append(reg.name)
    return [
        CapabilityInfo(name=name, description=name.replace("_", " ").title(), agents=agents)
        for name, agents in cap_map.items()
    ]


@router.get("/reflections", response_model=list[ReflectionInfo])
async def list_reflections(limit: int = 20):
    orchestrator = _get_orchestrator()
    return [
        ReflectionInfo(
            agent=r.agent_name,
            task=r.objective,
            verdict=r.verdict.value,
            confidence=r.confidence,
            duration_ms=r.duration_ms,
            error=r.error,
            timestamp=r.created_at,
        )
        for r in orchestrator.get_reflections(limit)
    ]
