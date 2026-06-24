
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


def _get_orchestrator() -> AgentOrchestrator:
    router_llm = ModelRouter()
    adapter = VectorStoreAdapter()
    return build_orchestrator(router_llm, adapter)


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
