from __future__ import annotations

import asyncio
from typing import Dict

from socialsim4.core.simtree import SimTree
from socialsim4.scenarios.basic import SCENES, make_clients_from_env


class SimTreeRecord:
    def __init__(self, tree: SimTree):
        self.tree = tree
        self.subs: list[asyncio.Queue] = []
        self.running: set[int] = set()


def _quiet_logger(event_type: str, data: dict) -> None:
    return


def _build_tree_for_scene(scene_type: str) -> SimTree:
    spec = SCENES.get(scene_type)
    if spec is None:
        raise ValueError(f"Unsupported scene type: {scene_type}")
    clients = make_clients_from_env()
    simulator = spec.builder(clients, _quiet_logger)
    tree = SimTree.new(simulator, clients)
    return tree


class SimTreeRegistry:
    def __init__(self) -> None:
        self._records: Dict[str, SimTreeRecord] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, simulation_id: str, scene_type: str) -> SimTreeRecord:
        key = simulation_id.upper()
        record = self._records.get(key)
        if record is not None:
            return record
        async with self._lock:
            record = self._records.get(key)
            if record is not None:
                return record
            tree = await asyncio.to_thread(_build_tree_for_scene, scene_type)
            record = SimTreeRecord(tree)
            # Forward all node log events to tree-level subscribers
            tree.set_tree_broadcast(
                lambda event: [q.put_nowait(event) for q in record.subs]
                if int(event["node"]) in record.running
                else None
            )
            self._records[key] = record
            return record

    def remove(self, simulation_id: str) -> None:
        self._records.pop(simulation_id.upper(), None)

    def get(self, simulation_id: str) -> SimTreeRecord | None:
        return self._records.get(simulation_id.upper())


SIM_TREE_REGISTRY = SimTreeRegistry()
