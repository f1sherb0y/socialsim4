from fastapi import FastAPI

from socialsimv4.api.routes import auth, feedback, personas, providers, simulation

app = FastAPI()

app.include_router(simulation.router, prefix="/simulation", tags=["simulation"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(providers.router, prefix="/providers", tags=["providers"])
app.include_router(personas.router, prefix="/personas", tags=["personas"])
app.include_router(feedback.router, prefix="/feedback", tags=["feedback"])


@app.get("/")
async def root():
    return {"message": "SocialSimv4 API"}
