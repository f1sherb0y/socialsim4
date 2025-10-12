from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...dependencies import get_current_user, get_db_session
from ...models.simulation import Simulation, SimulationLog, SimulationSnapshot
from ...schemas.common import Message
from ...schemas.simulation import (
    SimulationBase,
    SimulationCreate,
    SimulationLogEntry,
    SimulationUpdate,
    SnapshotBase,
    SnapshotCreate,
)
from ...schemas.user import UserPublic
from ...services.simulations import generate_simulation_name


router = APIRouter()


@router.get("/", response_model=list[SimulationBase])
async def list_simulations(
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[SimulationBase]:
    result = await session.execute(
        select(Simulation).where(Simulation.owner_id == current_user.id).order_by(Simulation.created_at.desc())
    )
    sims = result.scalars().all()
    return [SimulationBase.model_validate(sim) for sim in sims]


@router.post("/", response_model=SimulationBase, status_code=status.HTTP_201_CREATED)
async def create_simulation(
    payload: SimulationCreate,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SimulationBase:
    name = payload.name or generate_simulation_name()
    sim = Simulation(
        owner_id=current_user.id,
        name=name,
        scene_type=payload.scene_type,
        scene_config=payload.scene_config,
        agent_config=payload.agent_config,
        status="draft",
    )
    session.add(sim)
    await session.commit()
    await session.refresh(sim)
    return SimulationBase.model_validate(sim)


@router.get("/{simulation_id}", response_model=SimulationBase)
async def read_simulation(
    simulation_id: int,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SimulationBase:
    sim = await session.get(Simulation, simulation_id)
    if sim is None or sim.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")
    return SimulationBase.model_validate(sim)


@router.patch("/{simulation_id}", response_model=SimulationBase)
async def update_simulation(
    simulation_id: int,
    payload: SimulationUpdate,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SimulationBase:
    sim = await session.get(Simulation, simulation_id)
    if sim is None or sim.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")

    if payload.name is not None:
        sim.name = payload.name
    if payload.status is not None:
        sim.status = payload.status
    if payload.notes is not None:
        sim.notes = payload.notes

    await session.commit()
    await session.refresh(sim)
    return SimulationBase.model_validate(sim)


@router.delete("/{simulation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_simulation(
    simulation_id: int,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    sim = await session.get(Simulation, simulation_id)
    if sim is None or sim.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")
    await session.delete(sim)
    await session.commit()


@router.post("/{simulation_id}/save", response_model=SnapshotBase, status_code=status.HTTP_201_CREATED)
async def create_snapshot(
    simulation_id: int,
    payload: SnapshotCreate,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SnapshotBase:
    sim = await session.get(Simulation, simulation_id)
    if sim is None or sim.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")
    if sim.latest_state is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Simulation has no state to save")

    label = payload.label or f"Snapshot {datetime.now(timezone.utc).isoformat()}"
    turns = int(sim.latest_state.get("turns", 0)) if isinstance(sim.latest_state, dict) else 0
    snapshot = SimulationSnapshot(
        simulation_id=sim.id,
        label=label,
        state=sim.latest_state,
        turns=turns,
    )
    session.add(snapshot)
    await session.commit()
    await session.refresh(snapshot)
    return SnapshotBase.model_validate(snapshot)


@router.get("/{simulation_id}/snapshots", response_model=list[SnapshotBase])
async def list_snapshots(
    simulation_id: int,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[SnapshotBase]:
    sim = await session.get(Simulation, simulation_id)
    if sim is None or sim.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")
    result = await session.execute(
        select(SimulationSnapshot)
        .where(SimulationSnapshot.simulation_id == sim.id)
        .order_by(SimulationSnapshot.created_at.desc())
    )
    snapshots = result.scalars().all()
    return [SnapshotBase.model_validate(s) for s in snapshots]


@router.get("/{simulation_id}/logs", response_model=list[SimulationLogEntry])
async def list_logs(
    simulation_id: int,
    limit: int = 200,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[SimulationLogEntry]:
    sim = await session.get(Simulation, simulation_id)
    if sim is None or sim.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")
    result = await session.execute(
        select(SimulationLog)
        .where(SimulationLog.simulation_id == simulation_id)
        .order_by(SimulationLog.sequence.desc())
        .limit(limit)
    )
    logs = list(reversed(result.scalars().all()))
    return [SimulationLogEntry.model_validate(log) for log in logs]


@router.post("/{simulation_id}/start", response_model=Message)
async def start_simulation(
    simulation_id: int,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Message:
    sim = await session.get(Simulation, simulation_id)
    if sim is None or sim.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")

    sim.status = "running"
    sim.updated_at = datetime.now(timezone.utc)
    await session.commit()
    return Message(message="Simulation start enqueued")


@router.post("/{simulation_id}/resume", response_model=Message)
async def resume_simulation(
    simulation_id: int,
    snapshot_id: int | None = None,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Message:
    sim = await session.get(Simulation, simulation_id)
    if sim is None or sim.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")

    if snapshot_id is not None:
        snapshot = await session.get(SimulationSnapshot, snapshot_id)
        if snapshot is None or snapshot.simulation_id != sim.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")
        sim.latest_state = snapshot.state

    sim.status = "running"
    sim.updated_at = datetime.now(timezone.utc)
    await session.commit()
    return Message(message="Simulation resume enqueued")


@router.post("/{simulation_id}/copy", response_model=SimulationBase, status_code=status.HTTP_201_CREATED)
async def copy_simulation(
    simulation_id: int,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SimulationBase:
    sim = await session.get(Simulation, simulation_id)
    if sim is None or sim.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")

    new_sim = Simulation(
        owner_id=current_user.id,
        name=generate_simulation_name(),
        scene_type=sim.scene_type,
        scene_config=sim.scene_config,
        agent_config=sim.agent_config,
        latest_state=sim.latest_state,
        status="draft",
    )
    session.add(new_sim)
    await session.commit()
    await session.refresh(new_sim)
    return SimulationBase.model_validate(new_sim)
