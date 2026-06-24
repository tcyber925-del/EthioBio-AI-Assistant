from __future__ import annotations

import structlog

from src.core.agent_orchestrator.models import AgentCapability, AgentRegistration

logger = structlog.get_logger()


class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, AgentRegistration] = {}

    def register(self, registration: AgentRegistration) -> None:
        self._agents[registration.name] = registration
        logger.info("agent_registered", name=registration.name)

    def unregister(self, name: str) -> None:
        self._agents.pop(name, None)

    def get(self, name: str) -> AgentRegistration | None:
        return self._agents.get(name)

    def list_agents(self) -> list[AgentRegistration]:
        return list(self._agents.values())

    def find_by_capability(self, capability_name: str) -> list[AgentRegistration]:
        return [
            reg for reg in self._agents.values()
            if any(c.name == capability_name for c in reg.capabilities)
        ]

    def find_by_task(self, task: str) -> list[tuple[AgentRegistration, AgentCapability]]:
        task_lower = task.lower()
        matches: list[tuple[AgentRegistration, AgentCapability]] = []
        for reg in self._agents.values():
            for cap in reg.capabilities:
                if cap.name.lower() in task_lower or any(
                    kw in task_lower for kw in cap.name.lower().split("_")
                ):
                    matches.append((reg, cap))
                    break
        return matches

    def all_capabilities(self) -> list[AgentCapability]:
        caps: list[AgentCapability] = []
        for reg in self._agents.values():
            caps.extend(reg.capabilities)
        return caps
