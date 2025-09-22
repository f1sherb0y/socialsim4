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
            if name and name in self.sim.agents:
                yield name
            else:
                yield next(self._fallback)


class LLMModeratedOrdering(Ordering):
    NAME = "llm_moderated"

    def __init__(self, sim, moderator, names: list[str] | None = None):
        super().__init__(sim)
        # Fixed types in prototype: moderator must be an Agent object
        self.moderator = moderator
        # Freeze the scheduling candidate set at init time
        self.names: list[str] = list(names) if names is not None else list(sim.agents.keys())
        self._queue: list[str] = []

    def iter(self) -> Iterator[str]:
        while True:
            if not self._queue:
                self._refill_queue()
            if not self._queue:
                # Fallback to simple sequential if nothing produced
                self._queue.extend(list(self.names))
            yield self._queue.pop(0)

    def post_turn(self, agent_name: str) -> None:
        if not self._queue:
            self._refill_queue()

    def on_event(self, sim, event_type: str, data: dict) -> None:
        if not self._queue:
            self._refill_queue()

    def _refill_queue(self) -> None:
        names = self.names
        if not names:
            return
        mod = self.moderator

        # Nudge moderator to emit a schedule_order action only
        instruction = (
            "Scheduling request: choose 1..N agents from the list in order and emit a single "
            "<Action name=\"schedule_order\"><order>[\"A\",\"B\"]</order></Action>. "
            "Do not emit any other action or message."
        )
        mod.add_env_feedback(
            f"[Scheduling] Agents: {', '.join(names)}\n{instruction}"
        )
        # Ask the moderator to take exactly one step with initiative
        action_datas = mod.process(self.sim.clients, initiative=True, scene=self.sim.scene)
        # Require and execute exactly the scheduling action
        sched = None
        for a in (action_datas or []):
            if a and a.get("action") == "schedule_order":
                sched = a
                break
        if sched is None:
            raise ValueError("Moderator must emit schedule_order action during scheduling")
        self.sim.scene.parse_and_handle_action(sched, mod, self.sim)

    # Allow schedule action to push into the queue
    def add_to_queue(self, names: list[str]) -> None:
        # Validate and extend
        self._queue.extend([n for n in names if n in self.sim.agents])


ORDERING_MAP = {
    SequentialOrdering.NAME: SequentialOrdering,
    RandomOrdering.NAME: RandomOrdering,
    AsynchronousOrdering.NAME: AsynchronousOrdering,
    ControlledOrdering.NAME: ControlledOrdering,
    LLMModeratedOrdering.NAME: LLMModeratedOrdering,
}
