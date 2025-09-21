from fastapi import APIRouter, FastAPI

from socialsimv4.api import config
from socialsimv4.api.routes import auth, feedback, personas, providers, simulation

app = FastAPI()
router = APIRouter(prefix=config.API_PREFIX)

router.include_router(simulation.router, tags=["simulation"])
router.include_router(auth.router, tags=["auth"])
router.include_router(providers.router, tags=["providers"])
router.include_router(personas.router, tags=["personas"])
router.include_router(feedback.router, tags=["feedback"])


@router.get("/")
async def root():
    return {"message": "SocialSimv4 API"}


app.include_router(router)
