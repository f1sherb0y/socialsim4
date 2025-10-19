from __future__ import annotations

from pathlib import Path

from litestar import Litestar, Router
from litestar.config.cors import CORSConfig
from litestar.openapi import OpenAPIConfig
from litestar.static_files import StaticFilesConfig

from .api.routes import router as api_router
from .core.config import get_settings
from .core.database import engine
from .db.base import Base


async def _prepare_database() -> None:
    import socialsim4.backend.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def create_app() -> Litestar:
    settings = get_settings()

    cors_config = None
    if settings.allowed_origins:
        cors_config = CORSConfig(
            allow_origins=settings.allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    root_dir = Path(__file__).resolve().parents[3]
    dist_dir = Path(settings.frontend_dist_path or root_dir / "frontend" / "dist").resolve()
    index_file = dist_dir / "index.html"
    if not dist_dir.is_dir():
        raise RuntimeError(f"Frontend dist directory missing: {dist_dir}")
    if not index_file.is_file():
        raise RuntimeError(f"Frontend index.html missing: {index_file}")

    static_files_config = [
        StaticFilesConfig(path="/", directories=[str(dist_dir)], html_mode=True, name="frontend")
    ]

    api_prefix = settings.api_prefix or "/api"
    api_routes = Router(path=api_prefix, route_handlers=[api_router])

    return Litestar(
        route_handlers=[api_routes],
        on_startup=[_prepare_database],
        cors_config=cors_config,
        debug=settings.debug,
        root_path=settings.backend_root_path,
        openapi_config=OpenAPIConfig(title=settings.app_name),
        static_files_config=static_files_config,
    )


app = create_app()
