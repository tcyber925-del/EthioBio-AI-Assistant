from __future__ import annotations

import structlog

from src.agents.curriculum_agent import CurriculumAgent
from src.agents.diagnostic_assessment import DiagnosticAgent
from src.agents.diagram import DiagramAgent
from src.agents.forecast_agent import ForecastAgent
from src.agents.intervention_agent import InterventionAgent
from src.agents.lesson_planner import LessonPlannerAgent
from src.agents.misconception_agent import MisconceptionAgent
from src.agents.quiz import QuizAgent
from src.agents.research_agent import ResearchAgent
from src.agents.safety import SafetyAgent
from src.agents.student_progress import StudentProgressAgent
from src.agents.translator import TranslatorAgent
from src.agents.tutor_agent import TutorAgent
from src.core.agent_orchestrator.models import AgentCapability, AgentRegistration
from src.core.agent_orchestrator.orchestrator import AgentOrchestrator
from src.core.agent_orchestrator.registry import AgentRegistry
from src.llm.router import ModelRouter
from src.retrieval.adapter import VectorStoreAdapter

logger = structlog.get_logger()


def build_registry(
    router: ModelRouter,
    adapter: VectorStoreAdapter | None = None,
) -> AgentRegistry:
    registry = AgentRegistry()

    tutor = TutorAgent(llm_router=router)
    registry.register(
        AgentRegistration(
            agent=tutor,
            name="tutor_agent",
            description="Answers biology questions with RAG and Socratic tutoring",
            capabilities=[
                AgentCapability(
                    name="tutoring",
                    description="Answer questions with tutoring",
                )
            ],
        )
    )

    quiz = QuizAgent(llm_router=router, adapter=adapter)
    registry.register(
        AgentRegistration(
            agent=quiz,
            name="quiz_agent",
            description="Generates biology quizzes with configurable difficulty",
            capabilities=[
                AgentCapability(name="quiz_generation", description="Create quizzes"),
                AgentCapability(name="assessment_creation", description="Create assessments"),
            ],
        )
    )

    lesson = LessonPlannerAgent(llm_router=router)
    registry.register(
        AgentRegistration(
            agent=lesson,
            name="lesson_planner_agent",
            description="Generates structured lesson plans with differentiation and exit tickets",
            capabilities=[
                AgentCapability(name="lesson_planning", description="Create lesson plans")
            ],
        )
    )

    diagnostic = DiagnosticAgent(llm_router=router)
    registry.register(
        AgentRegistration(
            agent=diagnostic,
            name="diagnostic_agent",
            description="Generates diagnostic assessments to identify weak areas",
            capabilities=[
                AgentCapability(name="diagnostic_assessment", description="Diagnostic assessments"),
            ],
        )
    )

    translator = TranslatorAgent(llm_router=router)
    registry.register(
        AgentRegistration(
            agent=translator,
            name="translator_agent",
            description="Translates content between English and Amharic",
            capabilities=[AgentCapability(name="translation", description="Translate text")],
        )
    )

    safety = SafetyAgent(llm_router=router)
    registry.register(
        AgentRegistration(
            agent=safety,
            name="safety_agent",
            description="Reviews content for safety and hallucination",
            capabilities=[
                AgentCapability(name="safety_review", description="Safety check content")
            ],
        )
    )

    diagram = DiagramAgent(llm_router=router, adapter=adapter)
    registry.register(
        AgentRegistration(
            agent=diagram,
            name="diagram_agent",
            description="Generates biology diagrams",
            capabilities=[
                AgentCapability(name="diagram_generation", description="Generate diagrams")
            ],
        )
    )

    progress = StudentProgressAgent(llm_router=router)
    registry.register(
        AgentRegistration(
            agent=progress,
            name="student_progress_agent",
            description="Analyzes student progress and generates insights",
            capabilities=[AgentCapability(name="student_progress", description="Analyze progress")],
        )
    )

    curriculum = CurriculumAgent(llm_router=router)
    registry.register(
        AgentRegistration(
            agent=curriculum,
            name="curriculum_agent",
            description="Sequences curriculum content and pacing",
            capabilities=[
                AgentCapability(name="curriculum_planning", description="Plan curriculum")
            ],
        )
    )

    forecast = ForecastAgent(llm_router=router)
    registry.register(
        AgentRegistration(
            agent=forecast,
            name="forecast_agent",
            description="Forecasts student performance and identifies at-risk students",
            capabilities=[
                AgentCapability(name="performance_forecast", description="Forecast performance")
            ],
        )
    )

    intervention = InterventionAgent(llm_router=router)
    registry.register(
        AgentRegistration(
            agent=intervention,
            name="intervention_agent",
            description="Selects and evaluates educational interventions",
            capabilities=[
                AgentCapability(name="intervention_analysis", description="Analyze interventions")
            ],
        )
    )

    misconception = MisconceptionAgent(llm_router=router)
    registry.register(
        AgentRegistration(
            agent=misconception,
            name="misconception_agent",
            description="Detects and analyzes student misconceptions",
            capabilities=[
                AgentCapability(name="misconception_detection", description="Detect misconceptions")
            ],
        )
    )

    research = ResearchAgent(llm_router=router)
    registry.register(
        AgentRegistration(
            agent=research,
            name="research_agent",
            description="Searches and summarizes educational research",
            capabilities=[
                AgentCapability(name="research_synthesis", description="Synthesize research")
            ],
        )
    )

    logger.info("agent_registry_built", count=len(registry.list_agents()))
    return registry


def build_orchestrator(
    router: ModelRouter,
    adapter: VectorStoreAdapter | None = None,
) -> AgentOrchestrator:
    registry = build_registry(router, adapter)
    return AgentOrchestrator(registry)
