from __future__ import annotations

from fastapi import FastAPI

from app.config import get_settings
from app.routers import tasks as tasks_router
from db.session import engine
from models.task_models import AutomationTask, AutomationTaskEvent


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.api_title, version=settings.api_version)
    app.include_router(tasks_router.router)

    @app.on_event("startup")
    def _create_tables() -> None:
        AutomationTask.__table__.create(bind=engine, checkfirst=True)
        AutomationTaskEvent.__table__.create(bind=engine, checkfirst=True)

    return app


app = create_app()
