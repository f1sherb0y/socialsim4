from typing import Dict, List, Optional

from socialsim4.core.event import PublicEvent
from socialsim4.core.simulator import Simulator


class SimTree:
    def __init__(self, clients: Dict[str, object]):
        self.clients = clients
        self.nodes: Dict[int, dict] = {}
        self.children: Dict[int, List[int]] = {}
        self.root: Optional[int] = None
        self._seq: int = 0

    @classmethod
    def new(cls, sim: Simulator, clients: Dict[str, object]):
        tree = cls(clients)
        root_id = tree._next_id()
        # Store a live simulator object on the node; clone via serialize->deserialize
        snap = sim.to_dict()
        sim_clone = Simulator.from_dict(snap, clients)
        tree.nodes[root_id] = {
            "id": root_id,
            "parent": None,
            "depth": 0,
            "edge_type": "root",
            "ops": [],
            "sim": sim_clone,
        }
        tree.children[root_id] = []
        tree.root = root_id
        return tree

    def _next_id(self) -> int:
        i = self._seq
        self._seq = i + 1
        return i

    def _restore_sim(self, node_id: int) -> Simulator:
        # Clone the simulator by snapshotting the node's live sim
        base = self.nodes[node_id]["sim"]
        snap = base.to_dict()
        return Simulator.from_dict(snap, self.clients)

    def _save_child(self, parent_id: int, edge_type: str, ops: List[dict], sim: Simulator) -> int:
        nid = self._next_id()
        parent = self.nodes[parent_id]
        node = {
            "id": nid,
            "parent": parent_id,
            "depth": int(parent["depth"]) + 1,
            "edge_type": edge_type,
            "ops": ops,
            # Store the live simulator for this node
            "sim": sim,
        }
        self.nodes[nid] = node
        if parent_id not in self.children:
            self.children[parent_id] = []
        self.children[parent_id].append(nid)
        self.children[nid] = []
        return nid

    def advance(self, parent_id: int, turns: int = 1) -> int:
        sim = self._restore_sim(parent_id)
        sim.run(max_turns=int(turns))
        return self._save_child(parent_id, "advance", [{"op": "advance", "turns": int(turns)}], sim)

    def branch(self, parent_id: int, ops: List[dict]) -> int:
        sim = self._restore_sim(parent_id)
        for op in ops:
            name = op["op"]
            if name == "agent_ctx_append":
                ag = sim.agents[op["name"]]
                ag.short_memory.append(op["role"], op["content"])
            elif name == "agent_plan_replace":
                ag = sim.agents[op["name"]]
                ag.plan_state = op["plan_state"]
            elif name == "agent_props_patch":
                ag = sim.agents[op["name"]]
                updates = op["updates"]
                for k, v in updates.items():
                    ag.properties[k] = v
            elif name == "scene_state_patch":
                updates = op["updates"]
                for k, v in updates.items():
                    sim.scene.state[k] = v
            elif name == "public_broadcast":
                sim.broadcast(PublicEvent(op["text"]))
            else:
                raise ValueError("Unknown op: " + name)

        et = "multi"
        if len(ops) == 1:
            m = ops[0]["op"]
            if m == "agent_ctx_append":
                et = "agent_ctx"
            elif m == "agent_plan_replace":
                et = "agent_plan"
            elif m == "agent_props_patch":
                et = "agent_props"
            elif m == "scene_state_patch":
                et = "scene_state"
            elif m == "public_broadcast":
                et = "public_event"
        return self._save_child(parent_id, et, ops, sim)

    def lca(self, a: int, b: int) -> int:
        da = int(self.nodes[a]["depth"])
        db = int(self.nodes[b]["depth"]) 
        na = a
        nb = b
        while da > db:
            na = self.nodes[na]["parent"]
            da -= 1
        while db > da:
            nb = self.nodes[nb]["parent"]
            db -= 1
        while na != nb:
            na = self.nodes[na]["parent"]
            nb = self.nodes[nb]["parent"]
        return na

    def summaries(self) -> List[dict]:
        items: List[dict] = []
        for nid, node in self.nodes.items():
            turns = int(node["sim"].turns)
            parent = node["parent"]
            edges = []
            for cid in self.children.get(nid, []):
                c = self.nodes[cid]
                edges.append(
                    {
                        "to": cid,
                        "type": c["edge_type"],
                        "ops": c["ops"],
                    }
                )
            items.append(
                {
                    "id": nid,
                    "turns": turns,
                    "parent": parent,
                    "edges": edges,
                }
            )
        items.sort(key=lambda x: int(x["id"]))
        return items

    def leaves(self) -> List[int]:
        res: List[int] = []
        for nid in self.nodes.keys():
            if len(self.children.get(nid, [])) == 0:
                res.append(nid)
        res.sort()
        return res

    def max_depth(self) -> int:
        m = 0
        for n in self.nodes.values():
            d = int(n["depth"])
            if d > m:
                m = d
        return m

    def frontier(self, only_max_depth: bool = True) -> List[int]:
        lf = self.leaves()
        if not only_max_depth:
            return lf
        md = self.max_depth()
        res: List[int] = []
        for nid in lf:
            if int(self.nodes[nid]["depth"]) == md:
                res.append(nid)
        return res

    def advance_frontier(self, turns: int = 1, only_max_depth: bool = True) -> List[int]:
        res: List[int] = []
        for pid in self.frontier(only_max_depth=only_max_depth):
            cid = self.advance(pid, turns=int(turns))
            res.append(cid)
        return res

    def advance_selected(self, parent_ids: List[int], turns: int = 1) -> List[int]:
        res: List[int] = []
        for pid in parent_ids:
            cid = self.advance(int(pid), turns=int(turns))
            res.append(cid)
        return res

    def delete_subtree(self, node_id: int) -> None:
        if node_id == self.root:
            raise ValueError("Cannot delete root node")
        root_parent = self.nodes[node_id]["parent"]
        stack = [node_id]
        to_del: List[int] = []
        while stack:
            nid = stack.pop()
            to_del.append(nid)
            for c in self.children.get(nid, []):
                stack.append(c)
        for nid in to_del:
            if nid in self.children:
                del self.children[nid]
            if nid in self.nodes:
                del self.nodes[nid]
        if root_parent is not None:
            ch = self.children.get(root_parent, [])
            if node_id in ch:
                ch.remove(node_id)
                self.children[root_parent] = ch
        # Root is not allowed to be deleted; no adjustment needed here
