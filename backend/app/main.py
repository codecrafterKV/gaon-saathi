"""Gaon Saathi FastAPI application."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text

from app import __version__
from app.config import get_settings
from app.database import get_engine
from app.logging_config import safe_exception_summary
from app.routers import admin_auth, admin_complaints, admin_manage, public
from app.security.crypto import get_keyring
from app.security.middleware import BodySizeLimitMiddleware, SecurityHeadersMiddleware

log = logging.getLogger("gaon_saathi")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    settings.validate_secrets()
    get_keyring()
    if settings.storage_backend == "local":
        settings.evidence_dir.mkdir(parents=True, exist_ok=True)
    log.info("Gaon Saathi %s started (%s)", __version__, settings.app_env)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    docs = settings.enable_api_docs
    app = FastAPI(
        title="Gaon Saathi API",
        version=__version__,
        description="Anonymous village grievance platform",
        lifespan=lifespan,
        docs_url="/api/docs" if docs else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if docs else None,
    )

    # Middleware (last added = outermost).
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_request: Request, exc: RequestValidationError):
        fields: dict[str, str] = {}
        for err in exc.errors():
            loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
            fields.setdefault(loc[0] if loc else "request", err.get("msg", "Invalid value").removeprefix("Value error, "))
        message = next(iter(fields.values()), "Invalid request.")
        # Note: the submitted values are deliberately NOT echoed back.
        return JSONResponse(status_code=422, content={"detail": {"message": message, "fields": fields}})

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        route = request.scope.get("route")
        log.error("Unhandled error on %s: %s", getattr(route, "path", "unknown route"), safe_exception_summary(exc))
        return JSONResponse(status_code=500, content={"detail": "Something went wrong on our side. Please try again."})

    @app.get("/api/health", tags=["health"])
    def health():
        try:
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            db_ok = True
        except Exception:  # noqa: BLE001
            db_ok = False
        return JSONResponse(status_code=200 if db_ok else 503,
                            content={"status": "ok" if db_ok else "degraded", "database": db_ok, "version": __version__})

    app.include_router(public.router)
    app.include_router(admin_auth.router)
    app.include_router(admin_complaints.router)
    app.include_router(admin_manage.router)

    @app.api_route("/api/{_rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
    def api_not_found(_rest: str):
        raise HTTPException(status_code=404, detail="Not found.")

    _mount_frontend(app, settings.frontend_dist)
    return app


def _mount_frontend(app: FastAPI, dist: Path) -> None:
    """Serve the built React app (single page application) if it exists."""
    settings = get_settings()
    index = dist / "index.html"
    if not settings.serve_frontend or not index.is_file():
        @app.get("/", include_in_schema=False)
        def _no_frontend():
            return JSONResponse({
                "message": "Gaon Saathi API is running. The web app is not built yet: "
                           "run `npm run build` in the frontend folder, or use `npm run dev` during development.",
            })
        return

    dist_root = dist.resolve()

    @app.get("/{full_path:path}", include_in_schema=False)
    def _spa(full_path: str):
        if full_path:
            candidate = (dist_root / full_path).resolve()
            if candidate.is_file() and candidate.is_relative_to(dist_root):
                cache = "public, max-age=31536000, immutable" if full_path.startswith("assets/") else "public, max-age=3600"
                return FileResponse(candidate, headers={"Cache-Control": cache})
        return FileResponse(index, headers={"Cache-Control": "no-cache"})


app = create_app()
