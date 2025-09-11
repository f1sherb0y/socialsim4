from fastapi import APIRouter, FastAPI

from socialsimv4.api.routes import auth, feedback, personas, providers, simulation
from . import config

app = FastAPI()
router = APIRouter(prefix=config.API_PREFIX)

router.include_router(simulation.router, prefix="/simulation", tags=["simulation"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(providers.router, prefix="/providers", tags=["providers"])
router.include_router(personas.router, prefix="/personas", tags=["personas"])
router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])

@router.get("/")
async def root():
    return {"message": "SocialSimv4 API"}

app.include_router(router)
