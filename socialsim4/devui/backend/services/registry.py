from typing import Dict, List

from socialsim4.core.simtree import SimTree
from socialsim4.core.simulator import Simulator
from socialsim4.devui.backend.services.snapshots import DevEventBus


class SimRecord:
    def __init__(self, sim: Simulator, bus: DevEventBus, names):
        self.sim = sim
        self.bus = bus
        self.names = names
        self.offsets = {
            "events": 0,
            "mem": {n: {"count": 0, "last_len": 0} for n in names},
        }


SIMS: Dict[int, SimRecord] = {}


class SimTreeRecord:
    def __init__(self, tree: SimTree):
        self.tree = tree
        self.subs: List[object] = []  # asyncio.Queue list (typed loosely)
        self.running: set[int] = set()


TREES: Dict[int, SimTreeRecord] = {}

_SIM_ID = 0
_TREE_ID = 0


def next_sim_id() -> int:
    global _SIM_ID
    i = _SIM_ID
    _SIM_ID = i + 1
    return i


def next_tree_id() -> int:
    global _TREE_ID
    i = _TREE_ID
    _TREE_ID = i + 1
    return i
