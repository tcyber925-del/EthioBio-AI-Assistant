import asyncio
import json
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

from src.api import (
    activity,
    admin,
    agent_orchestrator,
    assignment,
    auth,
    bookmark,
    chat,
    collection,
    config,
    diagnostic,
    diagram,
    digital_twin,
    ekg,
    export,
    gamification,
    health,
    intelligence,
    intervention,
    knowledge,
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
    workspace,
)
from src.api import memory as memory_api
from src.api import oauth as oauth_api
from src.api.graph import router as graph_router
from src.api.intelligence.continue_learning_router import (
    router as continue_learning_router,
)
from src.api.internal import router as internal_router
from src.api.models import router as models_router
from src.api.retrieval import router as retrieval_router
from src.config import settings
from src.core.errors import AppError
from src.core.memory.router import router as memory_router
from src.core.monitoring import pipeline_monitor
from src.core.tracing import TraceRepository
from src.database.session import async_session_factory, close_db, init_db
from src.guardrails.input.middleware import add_rate_limit_middleware
from src.llm.router import ModelRouter
from src.observability.langsmith import post_feedback, setup_langsmith
from src.schemas.common import HealthResponse

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer() if __debug__ else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)

logger = structlog.get_logger()


def _init_sentry():
    """Initialize Sentry SDK if SENTRY_DSN is configured. No-op otherwise."""
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.asyncio import AsyncioIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[FastApiIntegration(), AsyncioIntegration()],
            traces_sample_rate=1.0,
            environment="production" if not settings.debug else "development",
        )
        logger.info("sentry_initialized")
    except ImportError:
        logger.warning("sentry_sdk_not_installed, skipping Sentry init")
    except Exception:
        logger.exception("sentry_init_failed")


def _json_safe(value):
    """Return a JSON-serializable copy of value, coercing unknown types to str.

    agent_traces.event_metadata is a JSON column; any non-serializable object
    (e.g. a uuid.UUID) would abort the whole INSERT and lose the trace.
    """
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return json.loads(json.dumps(value, default=str))


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
            user_id=trace.metadata.get("user_id"),
            grade_level=trace.metadata.get("grade_level"),
            language=trace.metadata.get("language"),
            intent=trace.metadata.get("intent"),
            nodes_visited=trace.nodes_visited or [],
            node_timings={k: v for k, v in trace.node_timings.items() if not k.endswith("_start")},
            metadata=_json_safe(
                {k: v for k, v in trace.metadata.items() if k not in ("user_message", "response")}
            ),
            duration_ms=trace.duration_ms,
        )
    except Exception:
        logger.exception("trace_persist_failed", trace_id=trace.trace_id)


_eval_judge = None
_eval_sampler = None
_eval_semaphore = asyncio.Semaphore(5)


async def _evaluate_trace(trace):
    async with _eval_semaphore:
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
            results = await evaluate_and_write(_eval_judge, user_message, response, context)
            run_id = trace.metadata.get("langsmith_run_id")
            if run_id:
                post_feedback(run_id, results)
        except Exception:
            logger.exception("eval_trace_failed", trace_id=trace.trace_id)


def _preload_models():
    """No-op: embeddings are served by OpenRouter (HTTP), never loaded in-process.

    Keeping fastembed out of the API process keeps the 512Mi free-tier
    instance well under its memory limit; loading it at boot burned ~250MiB
    for zero benefit.
    """
    logger.info("embedding_preload_skipped_openrouter")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_starting", name=settings.app_name)
    _init_sentry()
    await init_db()
    _preload_models()
    from src.guardrails.startup import run_startup_checks

    warnings = await run_startup_checks()
    if warnings:
        logger.warning("startup_checks_completed", warning_count=len(warnings))

    from src.observability.instrumentation import init_openllmetry, init_otel

    init_otel()
    init_openllmetry()
    setup_langsmith()

    from src.observability.health import health_registry as _health_registry

    if _health_registry:
        guardrail_modules = [
            "rate_limiter",
            "input_sanitizer",
            "prompt_injection",
            "conversation_context",
            "toxicity",
            "topic_enforcer",
            "pii_scanner",
            "tool_guard",
            "safety_node",
            "claim_verifier",
            "hallucination_detector",
        ]
        for name in guardrail_modules:
            _health_registry.register(name)

    repo = TraceRepository(async_session_factory())

    async def _on_trace_complete(trace):
        await _save_trace_from_pipeline(trace, repo)
        asyncio.create_task(_evaluate_trace(trace))

    pipeline_monitor.set_on_complete(lambda trace: asyncio.create_task(_on_trace_complete(trace)))

    _telegram_bot_app = None
    if settings.telegram_bot_token:
        try:
            from src.telegram.bot import build_app

            tg_app = build_app()
            await tg_app.initialize()

            webhook_url = settings.telegram_webhook_url
            webhook_secret = settings.telegram_webhook_secret
            if webhook_url:
                await tg_app.bot.set_webhook(
                    url=webhook_url,
                    secret_token=webhook_secret,
                    allowed_updates=["message", "callback_query"],
                )
                logger.info("bot_webhook_set", url=webhook_url)
            else:
                from telegram import BotCommand

                commands = [
                    BotCommand("start", "Show menu"),
                    BotCommand("help", "Show help"),
                    BotCommand("ask", "Ask a biology question"),
                    BotCommand("quiz", "Generate a quiz"),
                    BotCommand("grade", "Set your grade (7-12)"),
                    BotCommand("language", "Set language (en/am/both)"),
                    BotCommand("menu", "Show main menu"),
                    BotCommand("cancel", "Cancel current operation"),
                ]
                await tg_app.bot.set_my_commands(commands)
                await tg_app.updater.start_polling(
                    allowed_updates=["message", "callback_query"], drop_pending_updates=True
                )
            await tg_app.start()
            app.state.telegram_bot = tg_app
            _telegram_bot_app = tg_app
            logger.info("bot_started", mode="webhook" if webhook_url else "polling")
        except Exception:
            logger.exception("bot_start_failed")

    _pipeline_consumer_task = None
    try:
        from src.core.knowledge_registry import KnowledgeRegistry
        from src.core.pipeline.consumer import PipelineStreamConsumer
        from src.core.pipeline.service import PipelineOrchestrator
        from src.core.storage import LocalFileStorage
        from src.rag.embedder import Embedder
        from src.rag.vector_store import VectorStore

        _pipeline_consumer = PipelineStreamConsumer(
            pipeline=PipelineOrchestrator(
                registry=KnowledgeRegistry(async_session_factory()),
                storage=LocalFileStorage(),
                embedder=Embedder(),
                vector_store=VectorStore(
                    persist_directory=settings.vector_store_path,
                    collection_name=settings.collection_name,
                ),
                session_factory=async_session_factory(),
            ),
            storage=LocalFileStorage(),
            redis_url=settings.redis_url,
        )
        await _pipeline_consumer.start()
        _pipeline_consumer_task = asyncio.create_task(_pipeline_consumer.run_forever())
        logger.info("pipeline_consumer_started")
    except Exception:
        logger.warning("pipeline_consumer_unavailable, processing via inline background tasks only")

    yield

    if _telegram_bot_app is not None:
        try:
            await _telegram_bot_app.stop()
            await _telegram_bot_app.shutdown()
            logger.info("bot_shutdown_complete")
        except Exception:
            logger.exception("bot_shutdown_failed")

    if _pipeline_consumer_task is not None:
        _pipeline_consumer_task.cancel()
        try:
            await _pipeline_consumer_task
        except asyncio.CancelledError:
            pass
    await close_db()
    logger.info("app_shutdown")


app = FastAPI(
    title=settings.app_name,
    version="1.1.0",
    lifespan=lifespan,
)


async def _ping():
    return "pong"


async def _echo(data: dict):
    return data


app.add_api_route("/ping", _ping, methods=["GET"])
app.add_api_route("/echo", _echo, methods=["POST"])


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("middleware_unhandled_error")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "no-referrer"
    if not settings.debug:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


add_rate_limit_middleware(app, settings.redis_url)

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


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    logger.warning("app_error", code=exc.code, status=exc.status, path=str(request.url))
    return JSONResponse(status_code=exc.status, content=exc.to_dict())


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.exception("unhandled_error", path=str(request.url))
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "detail": "An unexpected error occurred"}},
    )


app.include_router(chat.router)
app.include_router(config.router)
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
app.include_router(health.router)
app.include_router(intervention.router)
app.include_router(intelligence.router)
app.include_router(continue_learning_router)
app.include_router(recovery.router)
app.include_router(notifications.router)
app.include_router(memory_router)
app.include_router(memory_api.router)
app.include_router(misconceptions.router)
app.include_router(activity.router)
app.include_router(knowledge.router)
app.include_router(retrieval_router)

app.include_router(workspace.router)
app.include_router(collection.router)
app.include_router(assignment.router)
app.include_router(bookmark.router)
app.include_router(agent_orchestrator.router)
app.include_router(auth.router)
app.include_router(oauth_api.router)
app.include_router(internal_router)

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


@app.get("/liveness")
async def liveness():
    """Process is alive. Return 200 if the event loop is running."""
    return {"status": "alive"}


@app.get("/readiness")
async def readiness():
    """Check all external dependencies. Returns 503 if any critical is down."""
    from sqlalchemy import text

    from src.database.session import async_session_factory

    checks = {"database": "ok", "redis": "ok", "ollama": "ok"}
    is_ready = True

    # Database
    try:
        factory = async_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        checks["database"] = "down"
        is_ready = False

    # Redis
    try:
        from src.redis_client import get_redis

        redis = await get_redis()
        await redis.ping()
    except Exception:
        checks["redis"] = "down"
        is_ready = False

    # Ollama (local or Cloud)
    try:
        router = ModelRouter()
        ollama_ok = await router.check_health()
        if not ollama_ok:
            checks["ollama"] = "down"
            is_ready = False
    except Exception:
        checks["ollama"] = "down"
        is_ready = False

    status_code = 200 if is_ready else 503

    return Response(
        content=__import__("json").dumps({"ready": is_ready, "checks": checks}),
        media_type="application/json",
        status_code=status_code,
    )


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics_endpoint():
    from src.observability.metrics import registry

    if not registry:
        return "# No metrics registry (disabled)\n"
    return registry.prometheus_text()


@app.post("/webhook")
async def telegram_webhook(request: Request):
    tg_app = getattr(app.state, "telegram_bot", None)
    if tg_app is None:
        logger.warning("webhook_no_bot_app")
        return Response(status_code=503, content='{"error":"bot not ready"}')

    if settings.telegram_webhook_secret:
        token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if token != settings.telegram_webhook_secret:
            logger.warning("webhook_invalid_secret_token")
            return Response(status_code=403, content='{"error":"forbidden"}')

    from telegram import Update

    json_data = await request.json()
    update = Update.de_json(json_data, tg_app.bot)
    await tg_app.process_update(update)
    return Response(status_code=200, content='{"ok":true}')


def run():
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=settings.debug)


if __name__ == "__main__":
    run()
