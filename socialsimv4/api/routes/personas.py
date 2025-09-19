from fastapi import APIRouter, Depends, HTTPException

from socialsimv4.api import auth, schemas
from socialsimv4.api.simulation_manager import simulation_manager

router = APIRouter()


@router.post("/generate_profiles_plan")
async def generate_profiles_plan_endpoint(
    req: schemas.ProfilePlanReq,
    current_user: schemas.User = Depends(auth.get_current_active_user),
):
    # This is a placeholder. In a real application, you would call your
    # profile generation logic here.
    return {"plan": f"Plan for {req.agent_count} agents in a {req.scene} scene."}


@router.post("/generate_profiles")
async def generate_profiles_endpoint(
    req: schemas.ProfilesReq,
    current_user: schemas.User = Depends(auth.get_current_active_user),
):
    # This is a placeholder.
    return {"profiles": ["profile1", "profile2"]}


@router.get("/get_persona/{sim_code}")
async def get_persona(
    sim_code: str, current_user: schemas.User = Depends(auth.get_current_active_user)
):
    simulator = simulation_manager.get_simulation(sim_code)
    if not simulator:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return {"personas": list(simulator.agents.keys())}


@router.get("/personas_info")
async def personas_info(
    sim_code: str, current_user: schemas.User = Depends(auth.get_current_active_user)
):
    simulator = simulation_manager.get_simulation(sim_code)
    if not simulator:
        raise HTTPException(status_code=404, detail="Simulation not found")
    persona_info = [agent.to_dict() for agent in simulator.agents.values()]
    return {"personas": persona_info}


@router.get("/persona_detail")
async def persona_detail(
    sim_code: str,
    agent_name: str,
    current_user: schemas.User = Depends(auth.get_current_active_user),
):
    simulator = simulation_manager.get_simulation(sim_code)
    if not simulator:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if agent_name not in simulator.agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent = simulator.agents[agent_name]
    return {"scratch": agent.to_dict(), "a_mem": {}, "s_mem": {}}
