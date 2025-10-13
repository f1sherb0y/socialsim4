import asyncio
from contextlib import suppress
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_session
from ...dependencies import get_current_user, get_db_session, settings
from ...models.simulation import Simulation, SimulationLog, SimulationSnapshot
from ...models.user import User
from ...schemas.common import Message
from ...schemas.simulation import SimulationBase, SimulationCreate, SimulationLogEntry, SimulationUpdate, SnapshotBase, SnapshotCreate
from ...schemas.simtree import (
    SimulationTreeAdvanceChainPayload,
    SimulationTreeAdvanceFrontierPayload,
    SimulationTreeAdvanceMultiPayload,
    SimulationTreeBranchPayload,
)
from ...schemas.user import UserPublic
from ...services.simtree_runtime import SIM_TREE_REGISTRY, SimTreeRecord
from ...services.simulations import generate_simulation_id, generate_simulation_name


router = APIRouter()


async def _get_simulation_for_owner(
    session: AsyncSession,
    owner_id: int,
    simulation_id: str,
) -> Simulation:
    result = await session.execute(
        select(Simulation).where(Simulation.owner_id == owner_id, Simulation.id == simulation_id.upper())
    )
    sim = result.scalar_one_or_none()
    if sim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")
    return sim


async def _get_tree_record(sim: Simulation) -> SimTreeRecord:
    try:
        return await SIM_TREE_REGISTRY.get_or_create(sim.id, sim.scene_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


async def _get_simulation_and_tree(
    session: AsyncSession,
    owner_id: int,
    simulation_id: str,
) -> tuple[Simulation, SimTreeRecord]:
    sim = await _get_simulation_for_owner(session, owner_id, simulation_id)
    record = await _get_tree_record(sim)
    return sim, record


async def _resolve_user_from_token(token: str, session: AsyncSession) -> User | None:
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.jwt_signing_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        return None
    subject = payload.get("sub")
    if subject is None:
        return None
    user = await session.get(User, int(subject))
    if user is None or not user.is_active:
        return None
    return user


def _broadcast(record: SimTreeRecord, event: dict) -> None:
    for queue in list(record.subs):
        queue.put_nowait(event)


async def _drain_websocket_messages(websocket: WebSocket) -> None:
    while True:
        try:
            await websocket.receive_text()
        except WebSocketDisconnect:
            break
        except Exception:
            break


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
    sim_id = generate_simulation_id()
    name = payload.name or generate_simulation_name(sim_id)
    sim = Simulation(
        id=sim_id,
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
    simulation_id: str,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SimulationBase:
    sim = await _get_simulation_for_owner(session, current_user.id, simulation_id)
    return SimulationBase.model_validate(sim)


@router.patch("/{simulation_id}", response_model=SimulationBase)
async def update_simulation(
    simulation_id: str,
    payload: SimulationUpdate,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SimulationBase:
    sim = await _get_simulation_for_owner(session, current_user.id, simulation_id)

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
    simulation_id: str,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    sim = await _get_simulation_for_owner(session, current_user.id, simulation_id)
    await session.delete(sim)
    await session.commit()
    SIM_TREE_REGISTRY.remove(simulation_id)


@router.post("/{simulation_id}/save", response_model=SnapshotBase, status_code=status.HTTP_201_CREATED)
async def create_snapshot(
    simulation_id: str,
    payload: SnapshotCreate,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SnapshotBase:
    sim = await _get_simulation_for_owner(session, current_user.id, simulation_id)
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
    simulation_id: str,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[SnapshotBase]:
    sim = await _get_simulation_for_owner(session, current_user.id, simulation_id)
    result = await session.execute(
        select(SimulationSnapshot)
        .where(SimulationSnapshot.simulation_id == sim.id)
        .order_by(SimulationSnapshot.created_at.desc())
    )
    snapshots = result.scalars().all()
    return [SnapshotBase.model_validate(s) for s in snapshots]


@router.get("/{simulation_id}/logs", response_model=list[SimulationLogEntry])
async def list_logs(
    simulation_id: str,
    limit: int = 200,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[SimulationLogEntry]:
    sim = await _get_simulation_for_owner(session, current_user.id, simulation_id)
    result = await session.execute(
        select(SimulationLog)
        .where(SimulationLog.simulation_id == sim.id)
        .order_by(SimulationLog.sequence.desc())
        .limit(limit)
    )
    logs = list(reversed(result.scalars().all()))
    return [SimulationLogEntry.model_validate(log) for log in logs]


@router.post("/{simulation_id}/start", response_model=Message)
async def start_simulation(
    simulation_id: str,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Message:
    sim = await _get_simulation_for_owner(session, current_user.id, simulation_id)

    sim.status = "running"
    sim.updated_at = datetime.now(timezone.utc)
    await session.commit()
    return Message(message="Simulation start enqueued")


@router.post("/{simulation_id}/resume", response_model=Message)
async def resume_simulation(
    simulation_id: str,
    snapshot_id: int | None = None,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Message:
    sim = await _get_simulation_for_owner(session, current_user.id, simulation_id)

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
    simulation_id: str,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SimulationBase:
    sim = await _get_simulation_for_owner(session, current_user.id, simulation_id)

    new_id = generate_simulation_id()
    new_sim = Simulation(
        id=new_id,
        owner_id=current_user.id,
        name=generate_simulation_name(new_id),
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


# --- Simulation tree endpoints ---


@router.get("/{simulation_id}/tree/graph")
async def simulation_tree_graph(
    simulation_id: str,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    _, record = await _get_simulation_and_tree(session, current_user.id, simulation_id)
    tree = record.tree
    attached_ids = {
        int(nid)
        for nid, node in tree.nodes.items()
        if node.get("depth") is not None
    }
    nodes = [
        {"id": int(node["id"]), "depth": int(node["depth"])}
        for node in tree.nodes.values()
        if node.get("depth") is not None
    ]
    edges = []
    for pid, children in tree.children.items():
        if pid not in attached_ids:
            continue
        for cid in children:
            if cid not in attached_ids:
                continue
            et = tree.nodes[cid]["edge_type"]
            edges.append({"from": int(pid), "to": int(cid), "type": et})
    depth_map = {
        int(node["id"]): int(node["depth"])
        for node in tree.nodes.values()
        if node.get("depth") is not None
    }
    outdeg = {i: 0 for i in depth_map}
    for edge in edges:
        outdeg[edge["from"]] = outdeg.get(edge["from"], 0) + 1
    leaves = [i for i, degree in outdeg.items() if degree == 0]
    max_depth = max(depth_map.values()) if depth_map else 0
    frontier = [i for i in leaves if depth_map.get(i) == max_depth]
    return {
        "root": int(tree.root) if tree.root is not None else None,
        "frontier": frontier,
        "running": [int(n) for n in record.running],
        "nodes": nodes,
        "edges": edges,
    }


@router.post("/{simulation_id}/tree/advance_frontier")
async def simulation_tree_advance_frontier(
    simulation_id: str,
    payload: SimulationTreeAdvanceFrontierPayload,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    _, record = await _get_simulation_and_tree(session, current_user.id, simulation_id)
    tree = record.tree
    parents = tree.frontier(True) if payload.only_max_depth else tree.leaves()
    turns = int(payload.turns)
    allocations = {pid: tree.copy_sim(pid) for pid in parents}
    for pid, cid in allocations.items():
        tree.attach(pid, [{"op": "advance", "turns": turns}], cid)
        node = tree.nodes[cid]
        _broadcast(
            record,
            {
                "type": "attached",
                "data": {
                    "node": int(cid),
                    "parent": int(pid),
                    "depth": int(node["depth"]),
                    "edge_type": node["edge_type"],
                    "ops": node["ops"],
                },
            },
        )
        record.running.add(cid)
        _broadcast(record, {"type": "run_start", "data": {"node": int(cid)}})
    # Yield control so WS tasks can flush newly enqueued 'attached' events
    await asyncio.sleep(0)

    async def _run(parent_id: int) -> tuple[int, int]:
        child_id = allocations[parent_id]
        simulator = tree.nodes[child_id]["sim"]
        await asyncio.to_thread(simulator.run, max_turns=turns)
        return parent_id, child_id

    results = await asyncio.gather(*[_run(pid) for pid in parents])
    produced: list[int] = []
    for _, cid in results:
        produced.append(cid)
        if cid in record.running:
            record.running.remove(cid)
        _broadcast(record, {"type": "run_finish", "data": {"node": int(cid)}})
    return {"children": [int(c) for c in produced]}


@router.post("/{simulation_id}/tree/advance_multi")
async def simulation_tree_advance_multi(
    simulation_id: str,
    payload: SimulationTreeAdvanceMultiPayload,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    _, record = await _get_simulation_and_tree(session, current_user.id, simulation_id)
    tree = record.tree
    parent = int(payload.parent)
    count = int(payload.count)
    if count <= 0:
        return {"children": []}
    turns = int(payload.turns)
    children = [tree.copy_sim(parent) for _ in range(count)]
    for cid in children:
        tree.attach(parent, [{"op": "advance", "turns": turns}], cid)
        node = tree.nodes[cid]
        _broadcast(
            record,
            {
                "type": "attached",
                "data": {
                    "node": int(cid),
                    "parent": int(parent),
                    "depth": int(node["depth"]),
                    "edge_type": node["edge_type"],
                    "ops": node["ops"],
                },
            },
        )
        record.running.add(cid)
        _broadcast(record, {"type": "run_start", "data": {"node": int(cid)}})
    await asyncio.sleep(0)

    async def _run(child_id: int) -> int:
        simulator = tree.nodes[child_id]["sim"]
        await asyncio.to_thread(simulator.run, max_turns=turns)
        return child_id

    finished = await asyncio.gather(*[_run(cid) for cid in children])
    result_children: list[int] = []
    for cid in finished:
        result_children.append(cid)
        if cid in record.running:
            record.running.remove(cid)
        _broadcast(record, {"type": "run_finish", "data": {"node": int(cid)}})
    return {"children": [int(c) for c in result_children]}


@router.post("/{simulation_id}/tree/advance_chain")
async def simulation_tree_advance_chain(
    simulation_id: str,
    payload: SimulationTreeAdvanceChainPayload,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    _, record = await _get_simulation_and_tree(session, current_user.id, simulation_id)
    tree = record.tree
    parent = int(payload.parent)
    steps = max(1, int(payload.turns))
    last = parent
    for _ in range(steps):
        cid = tree.copy_sim(last)
        tree.attach(last, [{"op": "advance", "turns": 1}], cid)
        node = tree.nodes[cid]
        _broadcast(
            record,
            {
                "type": "attached",
                "data": {
                    "node": int(cid),
                    "parent": int(last),
                    "depth": int(node["depth"]),
                    "edge_type": node["edge_type"],
                    "ops": node["ops"],
                },
            },
        )
        record.running.add(cid)
        _broadcast(record, {"type": "run_start", "data": {"node": int(cid)}})
        await asyncio.sleep(0)

        simulator = tree.nodes[cid]["sim"]
        await asyncio.to_thread(simulator.run, max_turns=1)

        if cid in record.running:
            record.running.remove(cid)
        _broadcast(record, {"type": "run_finish", "data": {"node": int(cid)}})
        last = cid
    return {"child": int(last)}


@router.post("/{simulation_id}/tree/branch")
async def simulation_tree_branch(
    simulation_id: str,
    payload: SimulationTreeBranchPayload,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    _, record = await _get_simulation_and_tree(session, current_user.id, simulation_id)
    tree = record.tree
    cid = tree.branch(int(payload.parent), [dict(op) for op in payload.ops])
    node = tree.nodes[cid]
    _broadcast(
        record,
        {
            "type": "attached",
            "data": {
                "node": int(cid),
                "parent": int(node["parent"]),
                "depth": int(node["depth"]),
                "edge_type": node["edge_type"],
                "ops": node["ops"],
            },
        },
    )
    return {"child": int(cid)}


@router.delete("/{simulation_id}/tree/node/{node_id}")
async def simulation_tree_delete_subtree(
    simulation_id: str,
    node_id: int,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    _, record = await _get_simulation_and_tree(session, current_user.id, simulation_id)
    try:
        record.tree.delete_subtree(int(node_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    _broadcast(record, {"type": "deleted", "data": {"node": int(node_id)}})
    return {"ok": True}


@router.get("/{simulation_id}/tree/sim/{node_id}/events")
async def simulation_tree_events(
    simulation_id: str,
    node_id: int,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list:
    _, record = await _get_simulation_and_tree(session, current_user.id, simulation_id)
    node = record.tree.nodes.get(int(node_id))
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    return node.get("logs", [])


@router.get("/{simulation_id}/tree/sim/{node_id}/state")
async def simulation_tree_state(
    simulation_id: str,
    node_id: int,
    current_user: UserPublic = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    _, record = await _get_simulation_and_tree(session, current_user.id, simulation_id)
    node = record.tree.nodes.get(int(node_id))
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    simulator = node["sim"]
    agents = []
    for name, agent in simulator.agents.items():
        agents.append(
            {
                "name": name,
                "role": agent.properties.get("role"),
                "plan_state": agent.plan_state,
                "short_memory": agent.short_memory.get_all(),
            }
        )
    return {"turns": simulator.turns, "agents": agents}


@router.websocket("/{simulation_id}/tree/events")
async def simulation_tree_events_ws(websocket: WebSocket, simulation_id: str) -> None:
    token = websocket.query_params.get("token")
    async with get_session() as session:
        user = await _resolve_user_from_token(token or "", session)
        if user is None:
            await websocket.close(code=1008)
            return
        try:
            sim = await _get_simulation_for_owner(session, user.id, simulation_id)
            record = await _get_tree_record(sim)
        except HTTPException:
            await websocket.close(code=1008)
            return

        await websocket.accept()
        queue: asyncio.Queue = asyncio.Queue()
        record.subs.append(queue)
        drain_task = asyncio.create_task(_drain_websocket_messages(websocket))
        try:
            while True:
                event = await queue.get()
                await websocket.send_json(event)
        except WebSocketDisconnect:
            pass
        finally:
            if queue in record.subs:
                record.subs.remove(queue)
            drain_task.cancel()
            with suppress(Exception):
                await drain_task


@router.websocket("/{simulation_id}/tree/{node_id}/events")
async def simulation_tree_node_events_ws(
    websocket: WebSocket,
    simulation_id: str,
    node_id: int,
) -> None:
    token = websocket.query_params.get("token")
    async with get_session() as session:
        user = await _resolve_user_from_token(token or "", session)
        if user is None:
            await websocket.close(code=1008)
            return
        try:
            sim = await _get_simulation_for_owner(session, user.id, simulation_id)
            record = await _get_tree_record(sim)
        except HTTPException:
            await websocket.close(code=1008)
            return

        if int(node_id) not in record.tree.nodes:
            await websocket.close(code=1008)
            return

        await websocket.accept()
        queue: asyncio.Queue = asyncio.Queue()
        record.tree.add_node_sub(int(node_id), queue)
        drain_task = asyncio.create_task(_drain_websocket_messages(websocket))
        try:
            while True:
                event = await queue.get()
                await websocket.send_json(event)
        except WebSocketDisconnect:
            pass
        finally:
            record.tree.remove_node_sub(int(node_id), queue)
            drain_task.cancel()
            with suppress(Exception):
                await drain_task
