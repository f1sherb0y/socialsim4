import json
import random
from typing import Callable, Iterator, Optional


class Ordering:
    NAME = "base"

    def __init__(self, sim):
        self.sim = sim

    def iter(self) -> Iterator[str]:
        raise NotImplementedError

    def post_turn(self, agent_name: str) -> None:
        pass

    # Optional event hook; default no-op. Simulator will call this if present.
    def on_event(self, sim, event_type: str, data: dict) -> None:
        pass


class SequentialOrdering(Ordering):
    NAME = "sequential"

    def iter(self) -> Iterator[str]:
        while True:
            for name in list(self.sim.agents.keys()):
                if name in self.sim.agents:
                    yield name


class RandomOrdering(Ordering):
    NAME = "random"

    def __init__(self, sim, seed: Optional[int] = None):
        super().__init__(sim)
        self.rng = random.Random(seed)

    def iter(self) -> Iterator[str]:
        while True:
            names = list(self.sim.agents.keys())
            if not names:
                break
            yield self.rng.choice(names)


class AsynchronousOrdering(SequentialOrdering):
    NAME = "asynchronous"
    # Simplified: same as sequential for this prototype.


class ControlledOrdering(Ordering):
    NAME = "controlled"

    def __init__(
        self, sim, next_fn: Optional[Callable[[object], Optional[str]]] = None
    ):
        super().__init__(sim)
        # next_fn(sim) -> next agent name (or None to fall back)
        self.next_fn = next_fn
        self._fallback = SequentialOrdering(sim).iter()

    def iter(self) -> Iterator[str]:
        while True:
            name = None
            if self.next_fn:
                name = self.next_fn(self.sim)
            if isinstance(name, str) and name in self.sim.agents:
                yield name
            else:
                yield next(self._fallback)


class LLMModeratedOrdering(Ordering):
    NAME = "llm_moderated"

    def __init__(self, sim, client_name: str = "chat"):
        super().__init__(sim)
        self.client_name = client_name
        self._queue: list[str] = []

    def iter(self) -> Iterator[str]:
        while True:
            if not self._queue:
                self._refill_queue()
            if not self._queue:
                # Fallback to simple sequential if LLM produced nothing
                self._queue.extend(list(self.sim.agents.keys()))
            yield self._queue.pop(0)

    def post_turn(self, agent_name: str) -> None:
        if not self._queue:
            self._refill_queue()

    def on_event(self, sim, event_type: str, data: dict) -> None:
        if not self._queue:
            self._refill_queue()

    def _refill_queue(self) -> None:
        client = (self.sim.clients or {}).get(self.client_name)
        names = list(self.sim.agents.keys())
        if not names:
            return
        if not client:
            self._queue.extend(names)
            return
        # Ask for a short schedule; allow 1..N names
        prompt = (
            "Schedule the next few agents to act. Choose 1..N names from the list, in order.\n"
            f"Agents: {', '.join(names)}\n"
            "Output ONLY a JSON array of names. Example: [\"Alice\", \"Bob\"]"
        )
        messages = [
            {"role": "system", "content": "You output only a JSON array of agent names."},
            {"role": "user", "content": prompt},
        ]
        txt = client.chat(messages) or "[]"
        start = txt.find("[")
        end = txt.find("]", start)
        arr = json.loads(txt[start : end + 1])
        # Validate and deduplicate while preserving order
        seen = set()
        batch: list[str] = []
        for n in arr:
            if isinstance(n, str) and n in self.sim.agents and n not in seen:
                seen.add(n)
                batch.append(n)
        if batch:
            self._queue.extend(batch)


ORDERING_MAP = {
    SequentialOrdering.NAME: SequentialOrdering,
    RandomOrdering.NAME: RandomOrdering,
    AsynchronousOrdering.NAME: AsynchronousOrdering,
    ControlledOrdering.NAME: ControlledOrdering,
    LLMModeratedOrdering.NAME: LLMModeratedOrdering,
}
