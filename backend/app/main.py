import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from starlette.routing import Mount

from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.api.logs import router as logs_router
from app.api.pages import router as pages_router
from app.api.projects import router as projects_router
from app.api.summary import router as summary_router
from app.api.version import router as version_router
from app.core.config import Settings
from app.core.settings import get_settings
from app.database.bootstrap import init_db
from app.utils.logging_config import configure_logging

startup_logger = logging.getLogger("layoutforge.startup")


def _run_startup_self_check(app: FastAPI, settings: Settings) -> None:
    """Explicit, named checks for the endpoints the frontend's contract
    depends on — distinct from the full route dump below. A 404 on either
    of these has happened in practice because of a stale backend process
    serving an old build; this makes "is the contract actually there"
    impossible to miss in application.log."""
    paths = {route.path for route in app.routes if isinstance(route, (APIRoute, Mount))}

    version_path = f"{settings.api_prefix}/version"
    if version_path in paths:
        startup_logger.info("[OK] %s", version_path)
    else:
        startup_logger.error("[FAIL] %s is NOT registered", version_path)

    health_path = f"{settings.api_prefix}/health"
    if health_path in paths:
        startup_logger.info("[OK] %s", health_path)
    else:
        startup_logger.error("[FAIL] %s is NOT registered", health_path)

    if "/static/projects" in paths:
        startup_logger.info("[OK] Static mount")
    else:
        startup_logger.error("[FAIL] Static mount is NOT registered")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.logs_dir)

    for directory in (settings.projects_dir, settings.cache_dir, settings.temp_dir, settings.logs_dir):
        directory.mkdir(parents=True, exist_ok=True)

    # A trivially-fetchable marker so the frontend's environment check can
    # confirm the static mount actually serves files from this directory,
    # without depending on any project existing yet. Created only if
    # missing — no reason to rewrite it on every restart.
    static_marker = settings.projects_dir / ".static_ok"
    if not static_marker.exists():
        static_marker.write_text("ok", encoding="utf-8")

    init_db()

    app = FastAPI(title=settings.app_name, version=settings.app_version)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(version_router, prefix=settings.api_prefix)
    app.include_router(projects_router, prefix=settings.api_prefix)
    app.include_router(jobs_router, prefix=settings.api_prefix)
    app.include_router(pages_router, prefix=settings.api_prefix)
    app.include_router(summary_router, prefix=settings.api_prefix)
    app.include_router(logs_router, prefix=settings.api_prefix)

    # Serves each project's generated HTML/CSS/resources directly so the
    # frontend ViewerEngine can fetch them by relative path and mount them
    # into a Shadow DOM. Read-only; nothing under storage/ is ever served
    # outside of a project's own directory.
    app.mount(
        "/static/projects", StaticFiles(directory=str(settings.projects_dir)), name="project-static"
    )

    # Startup validation: log every registered API route so a missing
    # endpoint (e.g. a router that failed to import, or didn't get
    # included) is visible in application.log immediately, not discovered
    # later as a confusing 404 in the frontend.
    for route in app.routes:
        if isinstance(route, APIRoute):
            methods = ",".join(sorted(route.methods or []))
            startup_logger.info("[OK] %-7s %s", methods, route.path)
    startup_logger.info("[OK] MOUNT   /static/projects -> %s", settings.projects_dir)

    _run_startup_self_check(app, settings)

    return app


app = create_app()
