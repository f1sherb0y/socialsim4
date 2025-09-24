from fastapi import APIRouter

from socialsim4.core.simtree import SimTree
from socialsim4.devui.backend.models.payloads import (
    SimTreeAdvanceFrontierPayload,
    SimTreeAdvancePayload,
    SimTreeAdvanceSelectedPayload,
    SimTreeBranchPayload,
    SimTreeCreatePayload,
    SimTreeCreateResult,
)
from socialsim4.devui.backend.services.factory import make_sim
from socialsim4.devui.backend.services.registry import TREES, next_tree_id


router = APIRouter(tags=["simtree"])


@router.post("/simtree", response_model=SimTreeCreateResult)
def create_tree(payload: SimTreeCreatePayload):
    sim, bus, names = make_sim(payload.scenario)
    tree = SimTree.new(sim, sim.clients)
    tree_id = next_tree_id()
    TREES[tree_id] = tree
    return {"id": tree_id, "root": int(tree.root)}


@router.get("/simtree/{tree_id}/summaries")
def tree_summaries(tree_id: int):
    t: SimTree = TREES[tree_id]
    return t.summaries()


@router.get("/simtree/{tree_id}/graph")
def tree_graph(tree_id: int):
    t: SimTree = TREES[tree_id]
    nodes = [{"id": int(n["id"]), "depth": int(n["depth"])} for n in t.nodes.values()]
    edges = []
    for pid, ch in t.children.items():
        for cid in ch:
            et = t.nodes[cid]["edge_type"]
            edges.append({"from": int(pid), "to": int(cid), "type": et})
    return {
        "root": int(t.root),
        "frontier": t.frontier(True),
        "nodes": nodes,
        "edges": edges,
    }


@router.post("/simtree/{tree_id}/advance")
def tree_advance(tree_id: int, payload: SimTreeAdvancePayload):
    t: SimTree = TREES[tree_id]
    cid = t.advance(int(payload.parent), int(payload.turns))
    return {"child": cid}


@router.post("/simtree/{tree_id}/advance_selected")
def tree_advance_selected(tree_id: int, payload: SimTreeAdvanceSelectedPayload):
    t: SimTree = TREES[tree_id]
    kids = t.advance_selected([int(x) for x in payload.parents], int(payload.turns))
    return {"children": kids}


@router.post("/simtree/{tree_id}/advance_frontier")
def tree_advance_frontier(tree_id: int, payload: SimTreeAdvanceFrontierPayload):
    t: SimTree = TREES[tree_id]
    kids = t.advance_frontier(int(payload.turns), bool(payload.only_max_depth))
    return {"children": kids}


@router.post("/simtree/{tree_id}/branch")
def tree_branch(tree_id: int, payload: SimTreeBranchPayload):
    t: SimTree = TREES[tree_id]
    cid = t.branch(int(payload.parent), [dict(x) for x in payload.ops])
    return {"child": cid}


@router.delete("/simtree/{tree_id}/node/{node_id}")
def tree_delete_subtree(tree_id: int, node_id: int):
    t: SimTree = TREES[tree_id]
    t.delete_subtree(int(node_id))
    return {"ok": True}

