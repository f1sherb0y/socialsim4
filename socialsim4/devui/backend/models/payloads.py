from typing import Dict, List, Literal

from pydantic import BaseModel


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


class SimTreeAdvanceMultiPayload(BaseModel):
    parent: int
    turns: int
    count: int


class SimTreeAdvanceChainPayload(BaseModel):
    parent: int
    turns: int
