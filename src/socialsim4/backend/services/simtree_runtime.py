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


def _build_tree_for_scene(scene_type: str, clients: dict | None = None) -> SimTree:
    spec = SCENES.get(scene_type)
    if spec is None:
        raise ValueError(f"Unsupported scene type: {scene_type}")
    active = clients or make_clients_from_env()
    simulator = spec.builder(active, _quiet_logger)
    tree = SimTree.new(simulator, active)
    return tree


class SimTreeRegistry:
    def __init__(self) -> None:
        self._records: Dict[str, SimTreeRecord] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, simulation_id: str, scene_type: str, clients: dict | None = None) -> SimTreeRecord:
        key = simulation_id.upper()
        record = self._records.get(key)
        if record is not None:
            return record
        async with self._lock:
            record = self._records.get(key)
            if record is not None:
                return record
            tree = await asyncio.to_thread(_build_tree_for_scene, scene_type, clients)
            record = SimTreeRecord(tree)
            # Wire event loop for thread-safe fanout
            loop = asyncio.get_running_loop()
            tree.attach_event_loop(loop)
            # Forward all node log events to tree-level subscribers (only for running nodes)
            def _fanout(event: dict) -> None:
                if int(event.get("node", -1)) not in record.running:
                    return
                for q in list(record.subs):
                    loop.call_soon_threadsafe(q.put_nowait, event)

            tree.set_tree_broadcast(_fanout)
            self._records[key] = record
            return record

    def remove(self, simulation_id: str) -> None:
        self._records.pop(simulation_id.upper(), None)

    def get(self, simulation_id: str) -> SimTreeRecord | None:
        return self._records.get(simulation_id.upper())


SIM_TREE_REGISTRY = SimTreeRegistry()
