import json
from typing import Dict, List, Tuple


class DevEventBus:
    def __init__(self, max_history: int = 5000):
        self.history: List[dict] = []
        self.max_history = max_history
        self.subs = []

    def subscribe(self, fn):
        self.subs.append(fn)

    def unsubscribe(self, fn):
        if fn in self.subs:
            self.subs.remove(fn)

    def publish(self, event_type: str, data: dict):
        self.history.append({"type": event_type, "data": data})
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history :]
        for fn in self.subs:
            fn(event_type, data)


def build_snapshot(sim, bus: DevEventBus, names: List[str], offsets: Dict) -> Tuple[Dict, Dict]:
    def _dc(x):
        return json.loads(json.dumps(x))

    new_mem_offsets: Dict[str, Dict[str, int]] = {}
    agents = []
    for nm in names:
        ag = sim.agents[nm]
        mem_all = ag.short_memory.get_all()
        prev = offsets["mem"].get(nm, {"count": 0, "last_len": 0})
        cnt = len(mem_all)

        delta_msgs = []
        if cnt == 0:
            new_last_len = 0
        elif cnt > int(prev.get("count", 0)):
            delta_msgs = mem_all[int(prev.get("count", 0)) :]
            new_last_len = len(mem_all[-1]["content"])
        else:
            last_content = mem_all[-1]["content"]
            prev_last_len = int(prev.get("last_len", 0))
            if len(last_content) > prev_last_len:
                appended = last_content[prev_last_len:]
                delta_msgs = [{"role": mem_all[-1]["role"], "content": appended}]
            new_last_len = len(last_content)

        new_mem_offsets[nm] = {"count": cnt, "last_len": new_last_len}
        agents.append(
            {
                "name": nm,
                "role": sim.agents[nm].properties.get("role"),
                "plan_state": _dc(sim.agents[nm].plan_state),
                "context_delta": _dc(delta_msgs),
            }
        )

    last_event_idx = offsets["events"]
    events_delta = _dc(bus.history[last_event_idx:])
    new_offsets = {"events": len(bus.history), "mem": new_mem_offsets}
    return (
        {
            "turns": sim.turns,
            "names": list(names),
            "events_delta": events_delta,
            "agents": agents,
        },
        new_offsets,
    )
