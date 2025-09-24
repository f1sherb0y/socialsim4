from typing import Dict, List

from socialsim4.core.simtree import SimTree


class SimTreeRecord:
    def __init__(self, tree: SimTree):
        self.tree = tree
        self.subs: List[object] = []  # asyncio.Queue list (typed loosely)
        self.running: set[int] = set()


TREES: Dict[int, SimTreeRecord] = {}

_TREE_ID = 0


def next_tree_id() -> int:
    global _TREE_ID
    i = _TREE_ID
    _TREE_ID = i + 1
    return i
