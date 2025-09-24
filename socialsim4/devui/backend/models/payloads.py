from typing import Dict, List, Literal, Optional

from pydantic import BaseModel


class SimCreatePayload(BaseModel):
    scenario: Literal["simple_chat"]


class SimCreateResult(BaseModel):
    id: int
    names: List[str]


class SimRunPayload(BaseModel):
    turns: int


class Offsets(BaseModel):
    events: int
    mem: Dict[str, Dict[str, int]]  # { name: {count, last_len} }


class SnapshotRequest(BaseModel):
    offsets: Offsets


class SimTreeCreatePayload(BaseModel):
    scenario: Literal["simple_chat"]


class SimTreeCreateResult(BaseModel):
    id: int
    root: int


class SimTreeAdvancePayload(BaseModel):
    parent: int
    turns: int


class SimTreeAdvanceSelectedPayload(BaseModel):
    parents: List[int]
    turns: int


class SimTreeAdvanceFrontierPayload(BaseModel):
    turns: int
    only_max_depth: bool = True


class SimTreeBranchPayload(BaseModel):
    parent: int
    ops: List[Dict]

