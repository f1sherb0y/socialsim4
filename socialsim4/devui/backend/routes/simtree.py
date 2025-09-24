import asyncio
import json

from fastapi import APIRouter, WebSocket

from socialsim4.core.simtree import SimTree
from socialsim4.core.simulator import Simulator
from socialsim4.devui.backend.models.payloads import (
    SimTreeAdvanceChainPayload,
    SimTreeAdvanceFrontierPayload,
    SimTreeAdvanceMultiPayload,
    SimTreeAdvancePayload,
    SimTreeAdvanceSelectedPayload,
    SimTreeBranchPayload,
    SimTreeCreatePayload,
    SimTreeCreateResult,
)
from socialsim4.devui.backend.services.factory import make_sim
from socialsim4.devui.backend.services.registry import (
    SIMS,
    TREES,
    SimRecord,
    SimTreeRecord,
    next_sim_id,
    next_tree_id,
)
from socialsim4.devui.backend.services.snapshots import DevEventBus

router = APIRouter(tags=["simtree"])


@router.post("/simtree", response_model=SimTreeCreateResult)
def create_tree(payload: SimTreeCreatePayload):
    sim, bus, names = make_sim(payload.scenario)
    tree = SimTree.new(sim, sim.clients)
    tree_id = next_tree_id()
    TREES[tree_id] = SimTreeRecord(tree)
    return {"id": tree_id, "root": int(tree.root)}


@router.get("/simtree/{tree_id}/summaries")
def tree_summaries(tree_id: int):
    t: SimTree = TREES[tree_id].tree
    return t.summaries()


@router.get("/simtree/{tree_id}/graph")
def tree_graph(tree_id: int):
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    nodes = [{"id": int(n["id"]), "depth": int(n["depth"])} for n in t.nodes.values()]
    edges = []
    for pid, ch in t.children.items():
        for cid in ch:
            et = t.nodes[cid]["edge_type"]
            edges.append({"from": int(pid), "to": int(cid), "type": et})
    return {
        "root": int(t.root),
        "frontier": t.frontier(True),
        "running": list(rec.running),
        "nodes": nodes,
        "edges": edges,
    }


@router.post("/simtree/{tree_id}/advance")
def tree_advance(tree_id: int, payload: SimTreeAdvancePayload):
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    cid = t.advance(int(payload.parent), int(payload.turns))
    for q in rec.subs:
        q.put_nowait(1)
    return {"child": cid}


@router.post("/simtree/{tree_id}/advance_selected")
async def tree_advance_selected(tree_id: int, payload: SimTreeAdvanceSelectedPayload):
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    parents = [int(x) for x in payload.parents]
    turns = int(payload.turns)
    for pid in parents:
        rec.running.add(pid)

    def _run_one(pid: int):
        logs: list = []
        sim = t._restore_sim(pid, logs)
        sim.run(max_turns=turns)
        return pid, sim, logs

    tasks = [asyncio.to_thread(_run_one, pid) for pid in parents]
    results = await asyncio.gather(*tasks)
    kids = []
    for pid, sim, logs in results:
        cid = t._save_child(
            pid, "advance", [{"op": "advance", "turns": turns}], sim, logs
        )
        kids.append(cid)
        if pid in rec.running:
            rec.running.remove(pid)
    for q in rec.subs:
        q.put_nowait(1)
    return {"children": kids}


@router.post("/simtree/{tree_id}/advance_frontier")
async def tree_advance_frontier(tree_id: int, payload: SimTreeAdvanceFrontierPayload):
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    pids = t.frontier(True) if bool(payload.only_max_depth) else t.leaves()
    turns = int(payload.turns)
    for pid in pids:
        rec.running.add(pid)

    def _run_one(pid: int):
        logs: list = []
        sim = t._restore_sim(pid, logs)
        sim.run(max_turns=turns)
        return pid, sim, logs

    tasks = [asyncio.to_thread(_run_one, pid) for pid in pids]
    results = await asyncio.gather(*tasks)
    kids = []
    for pid, sim, logs in results:
        cid = t._save_child(
            pid, "advance", [{"op": "advance", "turns": turns}], sim, logs
        )
        kids.append(cid)
        if pid in rec.running:
            rec.running.remove(pid)
    for q in rec.subs:
        q.put_nowait(1)
    return {"children": kids}


@router.post("/simtree/{tree_id}/branch")
def tree_branch(tree_id: int, payload: SimTreeBranchPayload):
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    cid = t.branch(int(payload.parent), [dict(x) for x in payload.ops])
    for q in rec.subs:
        q.put_nowait(1)
    return {"child": cid}


@router.delete("/simtree/{tree_id}/node/{node_id}")
def tree_delete_subtree(tree_id: int, node_id: int):
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    t.delete_subtree(int(node_id))
    for q in rec.subs:
        q.put_nowait(1)
    return {"ok": True}


@router.post("/simtree/{tree_id}/spawn_sim")
def tree_spawn_sim(tree_id: int, payload: dict):
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    node = int(payload.get("node", int(t.root)))
    base = t.nodes[node]["sim"]
    snap = base.to_dict()
    sim = Simulator.from_dict(snap, base.clients)
    bus = DevEventBus()
    sim.log_event = bus.publish
    for a in sim.agents.values():
        a.log_event = bus.publish
    names = list(sim.agents.keys())
    sid = next_sim_id()
    SIMS[sid] = SimRecord(sim, bus, names)
    return {"sim_id": sid, "names": names}


@router.post("/simtree/{tree_id}/advance_multi")
async def tree_advance_multi(tree_id: int, payload: SimTreeAdvanceMultiPayload):
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    parent = int(payload.parent)
    turns = int(payload.turns)
    count = int(payload.count)
    if count <= 0:
        return {"children": []}
    rec.running.add(parent)

    def _run_one(_: int):
        logs: list = []
        sim = t._restore_sim(parent, logs)
        sim.run(max_turns=turns)
        return sim, logs

    tasks = [asyncio.to_thread(_run_one, i) for i in range(count)]
    sims = await asyncio.gather(*tasks)
    kids = []
    for sim, logs in sims:
        cid = t._save_child(
            parent, "advance", [{"op": "advance", "turns": turns}], sim, logs
        )
        kids.append(cid)
    if parent in rec.running:
        rec.running.remove(parent)
    for q in rec.subs:
        q.put_nowait(1)
    return {"children": kids}


@router.post("/simtree/{tree_id}/advance_chain")
async def tree_advance_chain(tree_id: int, payload: SimTreeAdvanceChainPayload):
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    parent = int(payload.parent)
    turns = int(payload.turns)
    rec.running.add(parent)

    def _run():
        logs: list = []
        sim = t._restore_sim(parent, logs)
        sim.run(max_turns=turns)
        return sim, logs

    sim, logs = await asyncio.to_thread(_run)
    cid = t._save_child(
        parent, "advance", [{"op": "advance", "turns": turns}], sim, logs
    )
    if parent in rec.running:
        rec.running.remove(parent)
    for q in rec.subs:
        q.put_nowait(1)
    return {"child": cid}


@router.websocket("/simtree/{tree_id}/events")
async def simtree_events(tree_id: int, ws: WebSocket):
    await ws.accept()
    rec: SimTreeRecord = TREES[tree_id]
    q: asyncio.Queue = asyncio.Queue()
    rec.subs.append(q)
    try:
        # Optional initial message
        await ws.receive_text()
        while True:
            await q.get()
            t: SimTree = rec.tree
            nodes = [
                {"id": int(n["id"]), "depth": int(n["depth"])} for n in t.nodes.values()
            ]
            edges = []
            for pid, ch in t.children.items():
                for cid in ch:
                    et = t.nodes[cid]["edge_type"]
                    edges.append({"from": int(pid), "to": int(cid), "type": et})
            data = {
                "root": int(t.root),
                "frontier": t.frontier(True),
                "running": list(rec.running),
                "nodes": nodes,
                "edges": edges,
            }
            await ws.send_text(json.dumps(data))
    finally:
        rec.subs.remove(q)
