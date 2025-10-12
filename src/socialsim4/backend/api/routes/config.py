from fastapi import APIRouter

from ...core.config import get_settings


router = APIRouter()


@router.get("/")
async def read_config() -> dict:
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "debug": settings.debug,
        "allowed_origins": settings.allowed_origins,
    }
