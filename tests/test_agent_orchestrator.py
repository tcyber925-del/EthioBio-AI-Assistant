from src.core.agent_orchestrator.models import (
    AgentCapability,
    AgentMessage,
    AgentReflection,
    AgentRegistration,
    ReflectionVerdict,
)
from src.core.agent_orchestrator.registry import AgentRegistry


class TestAgentCapability:
    def test_create_capability(self):
        cap = AgentCapability(name="quiz_generation", description="Generate quizzes")
        assert cap.name == "quiz_generation"
        assert cap.requires_llm is True


class TestAgentRegistration:
    def test_create_registration(self):
        cap = AgentCapability(name="test", description="Test capability")
        reg = AgentRegistration(
            agent="mock",
            name="test_agent",
            description="A test agent",
            capabilities=[cap],
            version="2.0.0",
        )
        assert reg.name == "test_agent"
        assert reg.version == "2.0.0"
        assert reg.status.value == "idle"

    def test_default_status_idle(self):
        reg = AgentRegistration(
            agent="mock",
            name="default_agent",
            description="Default",
            capabilities=[],
        )
        assert reg.status.value == "idle"


class TestAgentMessage:
    def test_create_message(self):
        msg = AgentMessage(
            task_id="task-1",
            sender="quiz_agent",
            receiver="orchestrator",
            objective="Generate quiz on Cell Division",
            confidence=0.95,
        )
        assert msg.task_id == "task-1"
        assert msg.sender == "quiz_agent"
        assert msg.receiver == "orchestrator"
        assert msg.confidence == 0.95
        assert msg.message_id is not None


class TestAgentReflection:
    def test_success_reflection(self):
        ref = AgentReflection(
            agent_name="quiz_agent",
            task_id="task-1",
            objective="Generate quiz",
            verdict=ReflectionVerdict.success,
            confidence=0.9,
            duration_ms=1200,
        )
        assert ref.verdict == ReflectionVerdict.success
        assert ref.duration_ms == 1200
        assert ref.error is None

    def test_failure_reflection(self):
        ref = AgentReflection(
            agent_name="tutor_agent",
            task_id="task-2",
            objective="Answer question",
            verdict=ReflectionVerdict.failure,
            confidence=0.0,
            duration_ms=500,
            error="LLM timeout",
        )
        assert ref.error == "LLM timeout"


class TestAgentRegistry:
    def test_register_and_get(self):
        registry = AgentRegistry()
        cap = AgentCapability(name="test", description="Test")
        reg = AgentRegistration(
            agent="mock",
            name="my_agent",
            description="Agent",
            capabilities=[cap],
        )
        registry.register(reg)
        assert registry.get("my_agent") is reg
        assert registry.get("nonexistent") is None

    def test_find_by_capability(self):
        registry = AgentRegistry()
        q_cap = AgentCapability(name="quiz_generation", description="Quiz")
        a_cap = AgentCapability(name="assessment", description="Assessment")
        q_reg = AgentRegistration(
            agent="q",
            name="quiz_agent",
            description="",
            capabilities=[q_cap],
        )
        a_reg = AgentRegistration(
            agent="a",
            name="assess_agent",
            description="",
            capabilities=[a_cap],
        )
        registry.register(q_reg)
        registry.register(a_reg)

        matches = registry.find_by_capability("quiz_generation")
        assert len(matches) == 1
        assert matches[0].name == "quiz_agent"

    def test_find_by_capability_none(self):
        registry = AgentRegistry()
        assert registry.find_by_capability("nonexistent") == []

    def test_find_by_task(self):
        registry = AgentRegistry()
        cap = AgentCapability(name="quiz_generation", description="Quiz")
        reg = AgentRegistration(
            agent="q",
            name="quiz_agent",
            description="",
            capabilities=[cap],
        )
        registry.register(reg)

        matches = registry.find_by_task("Generate a quiz about cells")
        assert len(matches) >= 1
        assert matches[0][0].name == "quiz_agent"

    def test_find_by_task_no_match(self):
        registry = AgentRegistry()
        cap = AgentCapability(name="quiz_generation", description="Quiz")
        reg = AgentRegistration(
            agent="q",
            name="quiz_agent",
            description="",
            capabilities=[cap],
        )
        registry.register(reg)

        matches = registry.find_by_task("Do something completely unrelated")
        assert len(matches) == 0

    def test_list_agents(self):
        registry = AgentRegistry()
        registry.register(
            AgentRegistration(
                agent="a",
                name="a1",
                description="",
                capabilities=[],
            )
        )
        registry.register(
            AgentRegistration(
                agent="b",
                name="a2",
                description="",
                capabilities=[],
            )
        )
        assert len(registry.list_agents()) == 2

    def test_unregister(self):
        registry = AgentRegistry()
        registry.register(
            AgentRegistration(
                agent="x",
                name="x",
                description="",
                capabilities=[],
            )
        )
        registry.unregister("x")
        assert registry.get("x") is None

    def test_all_capabilities(self):
        registry = AgentRegistry()
        c1 = AgentCapability(name="a", description="A")
        c2 = AgentCapability(name="b", description="B")
        registry.register(
            AgentRegistration(
                agent="x",
                name="x",
                description="",
                capabilities=[c1, c2],
            )
        )
        assert len(registry.all_capabilities()) == 2
