import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from redis.asyncio import Redis

from src.api import (
    activity,
    admin,
    agent_orchestrator,
    auth,
    chat,
    diagnostic,
    diagram,
    digital_twin,
    ekg,
    export,
    gamification,
    intelligence,
    intervention,
    lesson,
    misconceptions,
    notifications,
    parent,
    progress,
    quiz,
    recovery,
    student,
    teacher,
    teacher_copilot,
    tracing,
    users,
)
from src.api.graph import router as graph_router
from src.api.intelligence.continue_learning_router import (
    router as continue_learning_router,
)
from src.api.models import router as models_router
from src.config import settings
from src.core.memory.router import router as memory_router
from src.core.monitoring import pipeline_monitor
from src.core.tracing import TraceRepository
from src.database.session import async_session_factory, close_db, init_db
from src.llm.router import ModelRouter
from src.schemas.common import HealthResponse

logger = structlog.get_logger()


async def _save_trace_from_pipeline(trace, repo):
    """Save a completed PipelineTrace to persistent storage."""
    try:
        end = datetime.fromtimestamp(trace.end_time, tz=timezone.utc) if trace.end_time else None
        await repo.save_trace(
            trace_id=trace.trace_id,
            start_time=datetime.fromtimestamp(trace.start_time, tz=timezone.utc),
            status=trace.status,
            user_message=trace.metadata.get("user_message", ""),
            response=trace.metadata.get("response"),
            end_time=end,
            error=trace.error,
            nodes_visited=trace.nodes_visited,
            node_timings={k: v for k, v in trace.node_timings.items() if not k.endswith("_start")},
            metadata={
                k: v for k, v in trace.metadata.items() if k not in ("user_message", "response")
            },
            duration_ms=trace.duration_ms,
        )
    except Exception:
        logger.exception("trace_persist_failed", trace_id=trace.trace_id)


_eval_judge = None
_eval_sampler = None


async def _evaluate_trace(trace):
    global _eval_judge, _eval_sampler
    from src.observability.evaluation.judge import LLMJudge
    from src.observability.evaluation.sampler import EvalSampler
    from src.observability.evaluation.writer import evaluate_and_write

    if _eval_sampler is None:
        _eval_sampler = EvalSampler()
    user_message = trace.metadata.get("user_message", "")
    response = trace.metadata.get("response", "")
    if not user_message or not response:
        return
    context = trace.metadata.get("context", "")
    is_error = trace.status == "failed"
    if not _eval_sampler.should_evaluate(is_error=is_error):
        return
    if _eval_judge is None:
        _eval_judge = LLMJudge()
    try:
        await evaluate_and_write(_eval_judge, user_message, response, context)
    except Exception:
        logger.exception("eval_trace_failed", trace_id=trace.trace_id)


def _preload_models():
    """Preload sentence-transformer models at startup."""
    from src.rag.embedder import _get_or_create_sentence_transformer
    from src.retrieval.reranker import _get_or_create_cross_encoder

    _get_or_create_sentence_transformer()
    _get_or_create_cross_encoder()
    logger.info("embedding_models_preloaded")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_starting", name=settings.app_name)
    await init_db()
    _preload_models()
    from src.guardrails.startup import run_startup_checks

    warnings = await run_startup_checks()
    if warnings:
        logger.warning("startup_checks_completed", warning_count=len(warnings))

    from src.observability.instrumentation import init_openllmetry, init_otel

    init_otel()
    init_openllmetry()

    from src.observability.health import health_registry as _health_registry

    if _health_registry:
        guardrail_modules = [
            "rate_limiter", "input_sanitizer", "prompt_injection",
            "conversation_context", "toxicity", "topic_enforcer",
            "pii_scanner", "tool_guard", "safety_node",
            "claim_verifier", "hallucination_detector",
        ]
        for name in guardrail_modules:
            _health_registry.register(name)

    repo = TraceRepository(async_session_factory)

    async def _on_trace_complete(trace):
        await _save_trace_from_pipeline(trace, repo)
        asyncio.create_task(_evaluate_trace(trace))

    pipeline_monitor.set_on_complete(
        lambda trace: asyncio.create_task(_on_trace_complete(trace))
    )
    yield
    await close_db()
    logger.info("app_shutdown")


app = FastAPI(
    title=settings.app_name,
    version="1.1.0",
    lifespan=lifespan,
)

_redis = Redis.from_url(settings.redis_url)
from src.guardrails.input.middleware import add_rate_limit_middleware
add_rate_limit_middleware(app, _redis)

_dev_origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]
_allowed = (
    [settings.dashboard_url] if settings.dashboard_url and not settings.debug else _dev_origins
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(quiz.router)
app.include_router(diagnostic.router)
app.include_router(lesson.router)
app.include_router(progress.router)
app.include_router(admin.router)
app.include_router(graph_router)
app.include_router(models_router)
app.include_router(diagram.router)
app.include_router(ekg.router)
app.include_router(digital_twin.router)
app.include_router(export.router)
app.include_router(gamification.router)
app.include_router(intervention.router)
app.include_router(intelligence.router)
app.include_router(continue_learning_router)
app.include_router(recovery.router)
app.include_router(notifications.router)
app.include_router(memory_router)
app.include_router(misconceptions.router)
app.include_router(activity.router)
app.include_router(agent_orchestrator.router)
app.include_router(auth.router)

app.include_router(parent.router)

app.include_router(teacher.router)
app.include_router(teacher_copilot.router)

app.include_router(student.router)
app.include_router(tracing.router)
app.include_router(users.router)
diagram_static_dir = Path("data/diagrams")
diagram_static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/diagrams/static", StaticFiles(directory=str(diagram_static_dir)), name="diagrams")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    router = ModelRouter()
    ollama_ok = await router.check_health()
    return HealthResponse(
        status="ok",
        ollama=ollama_ok,
        database=True,
    )


@app.get("/health/modules")
async def health_modules():
    from src.observability.health import health_registry

    if not health_registry:
        return {"overall_status": "disabled", "uptime_seconds": 0, "modules": []}
    return health_registry.to_dict(include_details=True)


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics_endpoint():
    from src.observability.metrics import registry

    if not registry:
        return "# No metrics registry (disabled)\n"
    return registry.prometheus_text()


def run():
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=settings.debug)


if __name__ == "__main__":
    run()
