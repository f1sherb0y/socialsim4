import asyncio
import json

from fastapi import APIRouter, HTTPException, WebSocket

from socialsim4.core.simtree import SimTree
from socialsim4.devui.backend.models.payloads import (
    SimTreeAdvanceChainPayload,
    SimTreeAdvanceFrontierPayload,
    SimTreeAdvanceMultiPayload,
    SimTreeAdvancePayload,
    SimTreeBranchPayload,
    SimTreeCreatePayload,
    SimTreeCreateResult,
)
from socialsim4.devui.backend.services.registry import (
    TREES,
    SimTreeRecord,
    next_tree_id,
)
from socialsim4.scripts.run_basic_scenes import (
    build_council_sim,
    build_landlord_sim,
    build_simple_chat_sim,
    build_simple_chat_sim_chinese,
    build_village_sim,  # village not tested by default
    build_werewolf_sim,
)

router = APIRouter(tags=["simtree"])


@router.post("/simtree", response_model=SimTreeCreateResult)
def create_tree(payload: SimTreeCreatePayload):
    sc = payload.scenario
    if sc == "simple_chat":
        sim = build_simple_chat_sim()
    elif sc == "simple_chat_chinese":
        sim = build_simple_chat_sim_chinese()
    elif sc == "council":
        sim = build_council_sim()
    elif sc == "werewolf":
        sim = build_werewolf_sim()
    elif sc == "landlord":
        sim = build_landlord_sim()
    elif sc == "village":
        sim = build_village_sim()
    else:
        raise ValueError("Unknown scenario: " + str(sc))

    tree = SimTree.new(sim, sim.clients)
    tree_id = next_tree_id()
    rec = SimTreeRecord(tree)
    TREES[tree_id] = rec
    # Emit initial attached for root (in case any subscribers are present)
    root_id = int(tree.root)
    root = tree.nodes[root_id]
    ev = {
        "type": "attached",
        "data": {
            "node": root_id,
            "parent": root.get("parent"),
            "depth": int(root.get("depth", 0) or 0),
            "edge_type": root.get("edge_type", "root"),
            "ops": root.get("ops", []),
        },
    }
    for q in rec.subs:
        q.put_nowait(ev)
    return {"id": tree_id, "root": int(tree.root)}


@router.get("/simtree")
def list_trees():
    res = []
    for tid, rec in TREES.items():
        t: SimTree = rec.tree
        res.append({"id": int(tid), "root": int(t.root)})
    res.sort(key=lambda x: int(x["id"]))
    return res


@router.get("/simtree/{tree_id}/summaries")
def tree_summaries(tree_id: int):
    if tree_id not in TREES:
        raise HTTPException(status_code=404, detail="simtree not found")
    t: SimTree = TREES[tree_id].tree
    return t.summaries()


@router.get("/simtree/{tree_id}/graph")
def tree_graph(tree_id: int):
    if tree_id not in TREES:
        raise HTTPException(status_code=404, detail="simtree not found")
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    # Filter out any not-yet-attached nodes (depth is None)
    attached_ids = {
        int(nid) for nid, n in t.nodes.items() if n.get("depth") is not None
    }
    nodes = [
        {"id": int(n["id"]), "depth": int(n["depth"])}
        for n in t.nodes.values()
        if n.get("depth") is not None
    ]
    edges = []
    for pid, ch in t.children.items():
        if pid not in attached_ids:
            continue
        for cid in ch:
            if cid not in attached_ids:
                continue
            et = t.nodes[cid]["edge_type"]
            edges.append({"from": int(pid), "to": int(cid), "type": et})
    # Compute frontier among attached nodes only
    depth_map = {
        int(n["id"]): int(n["depth"])
        for n in t.nodes.values()
        if n.get("depth") is not None
    }
    outdeg = {i: 0 for i in depth_map.keys()}
    for e in edges:
        outdeg[e["from"]] = outdeg.get(e["from"], 0) + 1
    leaves = [i for i, deg in outdeg.items() if deg == 0]
    maxd = max(depth_map.values()) if depth_map else 0
    frontier = [i for i in leaves if depth_map.get(i) == maxd]
    return {
        "root": int(t.root),
        "frontier": frontier,
        "running": list(rec.running),
        "nodes": nodes,
        "edges": edges,
    }


@router.post("/simtree/{tree_id}/advance")
def tree_advance(tree_id: int, payload: SimTreeAdvancePayload):
    if tree_id not in TREES:
        raise HTTPException(status_code=404, detail="simtree not found")
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    parent = int(payload.parent)
    turns = int(payload.turns)
    # Mark running and notify subscribers immediately so UI shows progress
    # Attach-first, then run with lifecycle events
    cid = t.copy_sim(parent)
    t.attach(parent, [{"op": "advance", "turns": turns}], cid)
    for q in rec.subs:
        q.put_nowait(
            {
                "type": "attached",
                "data": {
                    "node": int(cid),
                    "parent": int(parent),
                    "depth": int(t.nodes[cid]["depth"]),
                    "edge_type": t.nodes[cid]["edge_type"],
                    "ops": t.nodes[cid]["ops"],
                },
            }
        )
    rec.running.add(cid)
    for q in rec.subs:
        q.put_nowait({"type": "run_start", "data": {"node": int(cid)}})

    sim = t.nodes[cid]["sim"]
    sim.run(max_turns=turns)

    if cid in rec.running:
        rec.running.remove(cid)
    for q in rec.subs:
        q.put_nowait({"type": "run_finish", "data": {"node": int(cid)}})
    return {"child": cid}


@router.post("/simtree/{tree_id}/advance_frontier")
async def tree_advance_frontier(tree_id: int, payload: SimTreeAdvanceFrontierPayload):
    if tree_id not in TREES:
        raise HTTPException(status_code=404, detail="simtree not found")
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    pids = t.frontier(True) if bool(payload.only_max_depth) else t.leaves()
    turns = int(payload.turns)
    # Track running for child nodes only

    alloc: dict[int, int] = {pid: t.copy_sim(pid) for pid in pids}
    for pid, cid in alloc.items():
        t.attach(pid, [{"op": "advance", "turns": turns}], cid)
        for q in rec.subs:
            q.put_nowait(
                {
                    "type": "attached",
                    "data": {
                        "node": int(cid),
                        "parent": int(pid),
                        "depth": int(t.nodes[cid]["depth"]),
                        "edge_type": t.nodes[cid]["edge_type"],
                        "ops": t.nodes[cid]["ops"],
                    },
                }
            )
        rec.running.add(cid)
        for q in rec.subs:
            q.put_nowait({"type": "run_start", "data": {"node": int(cid)}})

    def _run_one(pid: int):
        cid = alloc[pid]
        sim = t.nodes[cid]["sim"]
        sim.run(max_turns=turns)
        return pid, cid

    tasks = [asyncio.to_thread(_run_one, pid) for pid in pids]
    results = await asyncio.gather(*tasks)
    kids = []
    for pid, cid in results:
        kids.append(cid)
        if cid in rec.running:
            rec.running.remove(cid)
        for q in rec.subs:
            q.put_nowait({"type": "run_finish", "data": {"node": int(cid)}})
    return {"children": kids}


@router.post("/simtree/{tree_id}/advance_chain")
async def tree_advance_chain(tree_id: int, payload: SimTreeAdvanceChainPayload):
    """Advance one step at a time for N steps, each step creates a new child."""
    if tree_id not in TREES:
        raise HTTPException(status_code=404, detail="simtree not found")
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    parent = int(payload.parent)
    steps = max(1, int(payload.turns))

    last_cid = parent
    for _ in range(steps):
        cid = t.copy_sim(last_cid)
        # Attach node (advance turns=1)
        t.attach(last_cid, [{"op": "advance", "turns": 1}], cid)
        for q in rec.subs:
            q.put_nowait(
                {
                    "type": "attached",
                    "data": {
                        "node": int(cid),
                        "parent": int(last_cid),
                        "depth": int(t.nodes[cid]["depth"]),
                        "edge_type": t.nodes[cid]["edge_type"],
                        "ops": t.nodes[cid]["ops"],
                    },
                }
            )
        rec.running.add(cid)
        for q in rec.subs:
            q.put_nowait({"type": "run_start", "data": {"node": int(cid)}})

        def _run_one():
            sim = t.nodes[cid]["sim"]
            sim.run(max_turns=1)
            return cid

        cid = await asyncio.to_thread(_run_one)
        if cid in rec.running:
            rec.running.remove(cid)
        for q in rec.subs:
            q.put_nowait({"type": "run_finish", "data": {"node": int(cid)}})
        last_cid = cid

    return {"child": last_cid}


@router.post("/simtree/{tree_id}/branch")
def tree_branch(tree_id: int, payload: SimTreeBranchPayload):
    if tree_id not in TREES:
        raise HTTPException(status_code=404, detail="simtree not found")
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    cid = t.branch(int(payload.parent), [dict(x) for x in payload.ops])
    node = t.nodes[cid]
    for q in rec.subs:
        q.put_nowait(
            {
                "type": "attached",
                "data": {
                    "node": int(cid),
                    "parent": int(node["parent"]),
                    "depth": int(node["depth"]),
                    "edge_type": node["edge_type"],
                    "ops": node["ops"],
                },
            }
        )
    return {"child": cid}


@router.delete("/simtree/{tree_id}/node/{node_id}")
def tree_delete_subtree(tree_id: int, node_id: int):
    if tree_id not in TREES:
        raise HTTPException(status_code=404, detail="simtree not found")
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    t.delete_subtree(int(node_id))
    for q in rec.subs:
        q.put_nowait({"type": "deleted", "data": {"node": int(node_id)}})
    return {"ok": True}


@router.get("/simtree/{tree_id}/node/{node_id}/logs")
def node_logs(tree_id: int, node_id: int):
    if tree_id not in TREES:
        raise HTTPException(status_code=404, detail="simtree not found")
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    return t.nodes[int(node_id)].get("logs", [])


@router.get("/simtree/{tree_id}/node/{node_id}/state")
def node_state(tree_id: int, node_id: int):
    if tree_id not in TREES:
        raise HTTPException(status_code=404, detail="simtree not found")
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    node = t.nodes[int(node_id)]
    sim = node["sim"]
    agents = []
    for name, ag in sim.agents.items():
        agents.append(
            {
                "name": name,
                "role": ag.properties.get("role"),
                "plan_state": ag.plan_state,
                "short_memory": ag.short_memory.get_all(),
            }
        )
    return {"turns": sim.turns, "agents": agents}


# --- Sim-scoped aliases (sim_id == node_id within a tree) ---
@router.get("/simtree/{tree_id}/sim/{sim_id}/events")
def sim_events(tree_id: int, sim_id: int):
    if tree_id not in TREES:
        raise HTTPException(status_code=404, detail="simtree not found")
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    return t.nodes[int(sim_id)].get("logs", [])


@router.get("/simtree/{tree_id}/sim/{sim_id}/state")
def sim_state(tree_id: int, sim_id: int):
    if tree_id not in TREES:
        raise HTTPException(status_code=404, detail="simtree not found")
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    node = t.nodes[int(sim_id)]
    sim = node["sim"]
    agents = []
    for name, ag in sim.agents.items():
        agents.append(
            {
                "name": name,
                "role": ag.properties.get("role"),
                "plan_state": ag.plan_state,
                "short_memory": ag.short_memory.get_all(),
            }
        )
    return {"turns": sim.turns, "agents": agents}


@router.post("/simtree/{tree_id}/advance_multi")
async def tree_advance_multi(tree_id: int, payload: SimTreeAdvanceMultiPayload):
    if tree_id not in TREES:
        raise HTTPException(status_code=404, detail="simtree not found")
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    parent = int(payload.parent)
    turns = int(payload.turns)
    count = int(payload.count)
    if count <= 0:
        return {"children": []}
    # parent marker not needed; we track running children only

    cids = [t.copy_sim(parent) for _ in range(count)]
    for cid in cids:
        t.attach(parent, [{"op": "advance", "turns": turns}], cid)
        for q in rec.subs:
            q.put_nowait(
                {
                    "type": "attached",
                    "data": {
                        "node": int(cid),
                        "parent": int(parent),
                        "depth": int(t.nodes[cid]["depth"]),
                        "edge_type": t.nodes[cid]["edge_type"],
                        "ops": t.nodes[cid]["ops"],
                    },
                }
            )
        rec.running.add(cid)
        for q in rec.subs:
            q.put_nowait({"type": "run_start", "data": {"node": int(cid)}})

    def _run_one(i: int):
        try:
            cid = cids[i]
            sim = t.nodes[cid]["sim"]
            sim.run(max_turns=turns)
        except Exception as e:
            print(f"Run one exception: {e}")
        return cid

    tasks = [asyncio.to_thread(_run_one, i) for i in range(count)]
    results = await asyncio.gather(*tasks)
    kids = []
    for cid in results:
        kids.append(cid)
        if cid in rec.running:
            rec.running.remove(cid)
        for q in rec.subs:
            q.put_nowait({"type": "run_finish", "data": {"node": int(cid)}})
    return {"children": kids}


@router.websocket("/simtree/{tree_id}/events")
async def simtree_events(tree_id: int, ws: WebSocket):
    await ws.accept()
    if tree_id not in TREES:
        await ws.close(code=1008)
        return
    rec: SimTreeRecord = TREES[tree_id]
    q: asyncio.Queue = asyncio.Queue()
    rec.subs.append(q)
    try:
        # Optional initial message
        await ws.receive_text()
        # Emit initial attached event for root
        t: SimTree = rec.tree
        root_id = int(t.root)
        root = t.nodes[root_id]
        await ws.send_text(
            json.dumps(
                {
                    "type": "attached",
                    "data": {
                        "node": root_id,
                        "parent": root.get("parent"),  # None for root
                        "depth": int(root.get("depth", 0) or 0),
                        "edge_type": root.get("edge_type", "root"),
                        "ops": root.get("ops", []),
                    },
                }
            )
        )
        while True:
            ev = await q.get()
            await ws.send_text(json.dumps(ev))
    finally:
        rec.subs.remove(q)


@router.websocket("/simtree/{tree_id}/sim/{node_id}/events")
async def sim_node_events(tree_id: int, node_id: int, ws: WebSocket):
    await ws.accept()
    if tree_id not in TREES:
        await ws.close(code=1008)
        return
    rec: SimTreeRecord = TREES[tree_id]
    t: SimTree = rec.tree
    if node_id not in t.nodes:
        await ws.close(code=1008)
        return
    q: asyncio.Queue = asyncio.Queue()
    t.add_node_sub(node_id, q)
    try:
        await ws.receive_text()
        # No initial full sync; client should have fetched baseline via HTTP
        while True:
            ev = await q.get()
            await ws.send_text(json.dumps(ev))
    finally:
        t.remove_node_sub(node_id, q)
