from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.simtree import router as simtree_router


app = FastAPI(title="SocialSim4 DevUI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simtree_router, prefix="/devui")


@app.get("/health")
def health():
    return {"ok": True}
