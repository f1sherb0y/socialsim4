import asyncio
import json
from fastapi import APIRouter, WebSocket

from socialsim4.devui.backend.models.payloads import (
    Offsets,
    SimCreatePayload,
    SimCreateResult,
    SimRunPayload,
    SnapshotRequest,
)
from socialsim4.devui.backend.services.factory import make_sim
from socialsim4.devui.backend.services.registry import SIMS, SimRecord, next_sim_id
from socialsim4.devui.backend.services.snapshots import build_snapshot


router = APIRouter(tags=["simulation"])


@router.post("/sim", response_model=SimCreateResult)
def create_sim(payload: SimCreatePayload):
    sim, bus, names = make_sim(payload.scenario)
    sim_id = next_sim_id()
    SIMS[sim_id] = SimRecord(sim, bus, names)
    return {"id": sim_id, "names": names}


@router.post("/sim/{sim_id}/run")
def run_sim(sim_id: int, payload: SimRunPayload):
    rec = SIMS[sim_id]
    rec.sim.run(max_turns=int(payload.turns))
    return {"ok": True}


@router.post("/sim/{sim_id}/snapshot")
def get_snapshot(sim_id: int, payload: SnapshotRequest):
    rec = SIMS[sim_id]
    snap, new_off = build_snapshot(rec.sim, rec.bus, rec.names, payload.offsets.model_dump())
    rec.offsets = new_off
    return {"snapshot": snap, "offsets": new_off}


@router.websocket("/sim/{sim_id}/events")
async def sim_events(sim_id: int, ws: WebSocket):
    await ws.accept()
    rec = SIMS[sim_id]
    q: asyncio.Queue = asyncio.Queue()

    def _on_event(event_type: str, data: dict):
        q.put_nowait(1)

    rec.bus.subscribe(_on_event)
    try:
        raw = await ws.receive_text()
        init = json.loads(raw)
        offsets = init.get("offsets")
        while True:
            await q.get()
            snap, new_off = build_snapshot(rec.sim, rec.bus, rec.names, offsets)
            offsets = new_off
            await ws.send_text(json.dumps({"snapshot": snap, "offsets": new_off}))
    finally:
        rec.bus.unsubscribe(_on_event)
