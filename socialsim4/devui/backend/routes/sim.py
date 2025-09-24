from fastapi import APIRouter

from socialsim4.devui.backend.models.payloads import (
    SnapshotRequest,
)
from socialsim4.devui.backend.services.registry import SIMS
from socialsim4.devui.backend.services.snapshots import build_snapshot

router = APIRouter(tags=["simulation"])


@router.post("/sim/{sim_id}/snapshot")
def get_snapshot(sim_id: int, payload: SnapshotRequest):
    rec = SIMS[sim_id]
    snap, new_off = build_snapshot(
        rec.sim, rec.bus, rec.names, payload.offsets.model_dump()
    )
    rec.offsets = new_off
    return {"snapshot": snap, "offsets": new_off}
