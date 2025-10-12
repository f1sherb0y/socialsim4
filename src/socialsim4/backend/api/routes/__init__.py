from fastapi import APIRouter

from . import auth, config, providers, scenes, simulations


router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(config.router, prefix="/config", tags=["config"])
router.include_router(scenes.router, prefix="/scenes", tags=["scenes"])
router.include_router(simulations.router, prefix="/simulations", tags=["simulations"])
router.include_router(providers.router, prefix="/providers", tags=["providers"])
