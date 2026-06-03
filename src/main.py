from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api import (
    activity,
    admin,
    auth,
    chat,
    diagram,
    export,
    gamification,
    intelligence,
    lesson,
    notifications,
    parent,
    progress,
    quiz,
    recovery,
    teacher,
)
from src.api.graph import router as graph_router
from src.api.intelligence.continue_learning_router import (
    router as continue_learning_router,
)
from src.api.models import router as models_router
from src.config import settings
from src.core.memory.router import router as memory_router
from src.database.session import close_db, init_db
from src.llm.router import ModelRouter
from src.schemas.common import HealthResponse

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_starting", name=settings.app_name)
    await init_db()
    yield
    await close_db()
    logger.info("app_shutdown")


app = FastAPI(
    title=settings.app_name,
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.dashboard_url, "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(quiz.router)
app.include_router(lesson.router)
app.include_router(progress.router)
app.include_router(admin.router)
app.include_router(graph_router)
app.include_router(models_router)
app.include_router(diagram.router)
app.include_router(export.router)
app.include_router(gamification.router)
app.include_router(intelligence.router)
app.include_router(continue_learning_router)
app.include_router(recovery.router)
app.include_router(notifications.router)
app.include_router(memory_router)
app.include_router(activity.router)
app.include_router(auth.router)

app.include_router(parent.router)

app.include_router(teacher.router)
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


def run():
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=settings.debug)


if __name__ == "__main__":
    run()
