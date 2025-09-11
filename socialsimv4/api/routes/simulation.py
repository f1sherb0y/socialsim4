import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from socialsimv4.core.action import (
    ExitGroupchatAction,
    SendMessageAction,
    SkipReplyAction,
)
from socialsimv4.core.actions.map_actions import (
    ExploreAction,
    GatherResourceAction,
    LookAroundAction,
    MoveToLocationAction,
    QuickMoveAction,
    RestAction,
)
from socialsimv4.core.agent import Agent
from socialsimv4.core.scenes.map_scene import MapScene
from socialsimv4.core.simulator import Simulator

from .. import auth, database, schemas
from ..simulation_manager import simulation_manager

router = APIRouter()

ACTION_SPACE_MAP = {
    "send_message": SendMessageAction(),
    "skip_reply": SkipReplyAction(),
    "exit_groupchat": ExitGroupchatAction(),
    "move_to_location": MoveToLocationAction(),
    "look_around": LookAroundAction(),
    "gather_resource": GatherResourceAction(),
    "rest": RestAction(),
    "quick_move": QuickMoveAction(),
    "explore": ExploreAction(),
}

SCENE_MAP = {
    "map_scene": MapScene,
}


@router.post("/start")
async def start_simulation(
    sim_code: str,
    template_id: int,
    current_user: schemas.User = Depends(auth.get_current_active_user),
    db: Session = Depends(database.SessionLocal),
):
    template = (
        db.query(database.SimulationTemplate)
        .filter(database.SimulationTemplate.id == template_id)
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    template_data = json.loads(template.template_json)

    agents = [
        Agent.from_dict(agent_data, ACTION_SPACE_MAP)
        for agent_data in template_data["agents"]
    ]

    scene_type = template_data["scenario"]["type"]
    scene_class = SCENE_MAP.get(scene_type)
    if not scene_class:
        raise HTTPException(status_code=400, detail=f"Unknown scene type: {scene_type}")
    scenario = scene_class.from_dict(template_data["scenario"])

    client = None

    simulator = Simulator(agents, scenario, client)

    if not simulation_manager.start_simulation(sim_code, simulator):
        raise HTTPException(status_code=400, detail="Simulation already running")

    return {"status": "success", "message": f"Simulation '{sim_code}' started."}


@router.get("/status")
async def get_simulation_status(
    sim_code: str, current_user: schemas.User = Depends(auth.get_current_active_user)
):
    simulator = simulation_manager.get_simulation(sim_code)
    if not simulator:
        raise HTTPException(status_code=404, detail="Simulation not found")

    return {"status": "running", "round": simulator.round_num}


@router.post("/run")
async def run_simulation(
    sim_code: str,
    rounds: int = 1,
    current_user: schemas.User = Depends(auth.get_current_active_user),
):
    simulator = simulation_manager.get_simulation(sim_code)
    if not simulator:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulator.run(max_rounds=simulator.round_num + rounds)

    return {
        "status": "success",
        "message": f"Ran simulation '{sim_code}' for {rounds} round(s).",
    }


@router.post("/save")
async def save_simulation(
    sim_code: str, current_user: schemas.User = Depends(auth.get_current_active_user)
):
    simulator = simulation_manager.get_simulation(sim_code)
    if not simulator:
        raise HTTPException(status_code=404, detail="Simulation not found")

    with open(f"{sim_code}.json", "w") as f:
        json.dump(simulator.to_dict(), f, indent=2)

    return {"status": "success", "message": f"Simulation '{sim_code}' saved."}


@router.post("/load")
async def load_simulation(
    sim_code: str, current_user: schemas.User = Depends(auth.get_current_active_user)
):
    try:
        with open(f"{sim_code}.json", "r") as f:
            data = json.load(f)

        client = None

        simulator = Simulator.from_dict(data, client, ACTION_SPACE_MAP)
        simulation_manager.simulations[sim_code] = simulator

        return {"status": "success", "message": f"Simulation '{sim_code}' loaded."}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Saved simulation not found")


# Templates Routes


@router.get("/fetch_templates")
async def fetch_templates(
    current_user: schemas.User = Depends(auth.get_current_active_user),
    db: Session = Depends(database.SessionLocal),
):
    templates = db.query(database.SimulationTemplate).all()
    return {"templates": templates}


@router.delete("/delete_template")
async def delete_template(
    template_id: int,
    current_user: schemas.User = Depends(auth.get_current_active_user),
    db: Session = Depends(database.SessionLocal),
):
    template = (
        db.query(database.SimulationTemplate)
        .filter(database.SimulationTemplate.id == template_id)
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    db.delete(template)
    db.commit()
    return {"status": "success"}


@router.get("/fetch_template")
async def fetch_template(
    template_id: int,
    current_user: schemas.User = Depends(auth.get_current_active_user),
    db: Session = Depends(database.SessionLocal),
):
    template = (
        db.query(database.SimulationTemplate)
        .filter(database.SimulationTemplate.id == template_id)
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"template": template}
