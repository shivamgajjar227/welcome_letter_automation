from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request
import uvicorn

from config import get_settings
from app.routers import tasks as tasks_router
from app.routers import webhooks as webhooks_router
from app.routers import data as data_router
from db.session import engine
from models.task_models import AutomationTask, AutomationTaskEvent


def create_app() -> FastAPI:
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

    settings = get_settings()
    app = FastAPI(title=settings.api_title, version=settings.api_version)
    app.include_router(tasks_router.router)
    app.include_router(webhooks_router.router)
    app.include_router(data_router.router)

    logger = logging.getLogger("app")
    logger.info("FastAPI application initialised", extra={"title": settings.api_title, "version": settings.api_version})

    @app.on_event("startup")
    def _create_tables() -> None:
        AutomationTask.__table__.create(bind=engine, checkfirst=True)
        AutomationTaskEvent.__table__.create(bind=engine, checkfirst=True)

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception during request", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Check application logs for details."},
        )

    return app


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.main:app" if settings.api_reload else app,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.tasks_log_level.lower(),
    )
