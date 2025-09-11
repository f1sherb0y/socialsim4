import json

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from socialsimv4.core.agent import Agent
from socialsimv4.core.simulator import Simulator
from socialsimv4.core.registry import SCENE_MAP

import os
from socialsimv4.api import auth, database, schemas, config
from socialsimv4.api.simulation_manager import simulation_manager

router = APIRouter()

from socialsimv4.core.llm import create_llm_client

@router.post("/start")
async def start_simulation(
    req: schemas.StartReq,
    current_user: schemas.User = Depends(auth.get_current_active_user),
    db: AsyncSession = Depends(database.get_db),
):
    result = await db.execute(
        select(database.SimulationTemplate).filter(database.SimulationTemplate.id == req.template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    template_data = json.loads(template.template_json)

    agents = [
        Agent.from_dict(agent_data)
        for agent_data in template_data["agents"]
    ]

    scene_type = template_data["scenario"]["type"]
    scene_class = SCENE_MAP.get(scene_type)
    if not scene_class:
        raise HTTPException(status_code=400, detail=f"Unknown scene type: {scene_type}")
    scenario = scene_class.from_dict(template_data["scenario"])

    # Create a dictionary of clients, keyed by provider name
    clients = {provider.name: create_llm_client(provider) for provider in req.providers}

    if not simulation_manager.start_simulation(req.sim_code, agents, scenario, clients):
        raise HTTPException(status_code=400, detail="Simulation already running")

    return {"status": "success", "message": f"Simulation '{req.sim_code}' started."}


@router.get("/status")
async def get_simulation_status(
    sim_code: str, current_user: schemas.User = Depends(auth.get_current_active_user)
):
    instance = simulation_manager.get_simulation(sim_code)
    if not instance:
        raise HTTPException(status_code=404, detail="Simulation not found")

    return {"status": "running", "round": instance.simulator.round_num}


@router.post("/run")
async def run_simulation(
    sim_code: str,
    rounds: int = 1,
    current_user: schemas.User = Depends(auth.get_current_active_user),
):
    instance = simulation_manager.get_simulation(sim_code)
    if not instance:
        raise HTTPException(status_code=404, detail="Simulation not found")

    instance.simulator.run(max_rounds=instance.simulator.round_num + rounds)

    return {
        "status": "success",
        "message": f"Ran simulation '{sim_code}' for {rounds} round(s).",
    }


@router.post("/save")
async def save_simulation(
    sim_code: str, current_user: schemas.User = Depends(auth.get_current_active_user)
):
    instance = simulation_manager.get_simulation(sim_code)
    if not instance:
        raise HTTPException(status_code=404, detail="Simulation not found")

    save_path = os.path.join(config.STORAGE_PATH, f"{sim_code}.json")
    with open(save_path, "w") as f:
        json.dump(instance.simulator.to_dict(), f, indent=2)

    return {"status": "success", "message": f"Simulation '{sim_code}' saved."}


@router.post("/load")
async def load_simulation(
    req: schemas.LoadReq,
    current_user: schemas.User = Depends(auth.get_current_active_user),
    db: AsyncSession = Depends(database.get_db),
):
    try:
        load_path = os.path.join(config.STORAGE_PATH, f"{req.sim_code}.json")
        with open(load_path, "r") as f:
            data = json.load(f)

        providers = req.providers
        if not providers:
            result = await db.execute(
                select(database.Provider).filter(database.Provider.username == current_user.username)
            )
            db_providers = result.scalars().all()
            providers = [schemas.LLMConfig.from_orm(p) for p in db_providers]

        clients = {provider.name: create_llm_client(provider) for provider in providers}

        simulation_manager.load_simulation(req.sim_code, data, clients)

        return {"status": "success", "message": f"Simulation '{req.sim_code}' loaded."}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Saved simulation not found")


@router.websocket("/ws/{sim_code}")
async def websocket_endpoint(websocket: WebSocket, sim_code: str):
    await websocket.accept()
    instance = simulation_manager.get_simulation(sim_code)
    if not instance:
        await websocket.close(code=1008, reason="Simulation not found")
        return

    instance.add_websocket(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep the connection alive
    except WebSocketDisconnect:
        instance.remove_websocket(websocket)


# Templates Routes


@router.get("/fetch_templates")
async def fetch_templates(
    current_user: schemas.User = Depends(auth.get_current_active_user),
    db: AsyncSession = Depends(database.get_db),
):
    result = await db.execute(select(database.SimulationTemplate))
    templates = result.scalars().all()
    return {"templates": templates}


@router.delete("/delete_template")
async def delete_template(
    template_id: int,
    current_user: schemas.User = Depends(auth.get_current_active_user),
    db: AsyncSession = Depends(database.get_db),
):
    result = await db.execute(
        select(database.SimulationTemplate).filter(database.SimulationTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    await db.delete(template)
    await db.commit()
    return {"status": "success"}


@router.get("/fetch_template")
async def fetch_template(
    template_id: int,
    current_user: schemas.User = Depends(auth.get_current_active_user),
    db: AsyncSession = Depends(database.get_db),
):
    result = await db.execute(
        select(database.SimulationTemplate).filter(database.SimulationTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"template": template}
