from datetime import datetime

from pydantic import BaseModel


class SimulationBase(BaseModel):
    id: int
    name: str
    scene_type: str
    scene_config: dict
    agent_config: dict
    latest_state: dict | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class SimulationCreate(BaseModel):
    name: str | None = None
    scene_type: str
    scene_config: dict
    agent_config: dict


class SimulationUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    notes: str | None = None


class SnapshotBase(BaseModel):
    id: int
    label: str
    turns: int
    state: dict
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class SnapshotCreate(BaseModel):
    label: str | None = None


class SimulationLogEntry(BaseModel):
    id: int
    event_type: str
    payload: dict
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}
