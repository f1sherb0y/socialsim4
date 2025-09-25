import json
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
    def new(
        cls,
        sim: Simulator,
        clients: Dict[str, object],
    ):
        tree = cls(clients)
        root_id = tree._next_id()
        # Store a live simulator object on the node; clone via serialize->deserialize
        snap = sim.to_dict()
        sim_clone = Simulator.from_dict(snap, clients, log_handler=None)
        root_logs: List[dict] = []
        tree.nodes[root_id] = {
            "id": root_id,
            "parent": None,
            "depth": 0,
            "edge_type": "root",
            "ops": [],
            "sim": sim_clone,
            "logs": root_logs,
        }
        # Attach log handler so future events at root accumulate into root logs
        tree._attach_log_handler(sim_clone, root_logs)
        sim.emit_remaining_events()
        tree.children[root_id] = []
        tree.root = root_id
        return tree

    def _next_id(self) -> int:
        i = self._seq
        self._seq = i + 1
        return i

    def copy_sim(self, node_id: int) -> int:
        # Clone the simulator by snapshotting the node's live sim
        base = self.nodes[node_id]["sim"]
        snap = base.to_dict()
        # Deep-copy the snapshot to avoid sharing nested lists/dicts
        deep = json.loads(json.dumps(snap))
        sim_copy = Simulator.from_dict(deep, self.clients, log_handler=None)

        # Prepare a new node with inherited logs snapshot; parent/ops assigned later
        nid = self._next_id()
        parent_logs = list(self.nodes[node_id].get("logs", []))
        # Deep copy parent's logs so child does not share dict references
        child_logs: List[dict] = json.loads(json.dumps(parent_logs))
        node = {
            "id": nid,
            "parent": None,
            "depth": None,
            "edge_type": None,
            "ops": [],
            "sim": sim_copy,
            "logs": child_logs,
        }

        self._attach_log_handler(sim_copy, child_logs)
        self.nodes[nid] = node
        self.children[nid] = []
        return nid

    def _attach_log_handler(self, sim: Simulator, logs: List[dict]) -> None:
        def _lh(kind, data):
            logs.append({"type": kind, "data": data})

        sim.log_event = _lh
        for a in sim.agents.values():
            a.log_event = _lh

    def attach(self, parent_id: int, ops: List[dict], cid: int) -> int:
        parent = self.nodes[parent_id]
        node = self.nodes[cid]
        node["parent"] = parent_id
        node["depth"] = int(parent["depth"]) + 1
        node["ops"] = ops
        et = "multi"
        if ops and len(ops) == 1:
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
            elif m == "advance":
                et = "advance"
        node["edge_type"] = et
        if parent_id not in self.children:
            self.children[parent_id] = []
        self.children[parent_id].append(cid)
        return cid

    # _save_child removed: parent/ops are assigned by the caller after copy_sim

    def advance(self, parent_id: int, turns: int = 1) -> int:
        cid = self.copy_sim(parent_id)
        sim = self.nodes[cid]["sim"]
        sim.run(max_turns=int(turns))
        return self.attach(parent_id, [{"op": "advance", "turns": int(turns)}], cid)

    def branch(self, parent_id: int, ops: List[dict]) -> int:
        cid = self.copy_sim(parent_id)
        sim = self.nodes[cid]["sim"]
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

        # Flush any queued events to logs
        sim.emit_remaining_events()
        return self.attach(parent_id, ops, cid)

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

    def advance_frontier(
        self, turns: int = 1, only_max_depth: bool = True
    ) -> List[int]:
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
