import random
from typing import Callable, Iterator, Optional


class Ordering:
    NAME = "base"

    def __init__(self):
        pass

    def set_simulation(self, sim) -> None:
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


class CycledOrdering(Ordering):
    NAME = "cycled"

    def __init__(self, names):
        self.names = names

    def iter(self) -> Iterator[str]:
        while True:
            for name in self.names:
                yield name


class RandomOrdering(Ordering):
    NAME = "random"

    def __init__(self, seed: Optional[int] = None):
        super().__init__()
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

    def __init__(self, next_fn: Optional[Callable[[object], Optional[str]]] = None):
        super().__init__()
        self.next_fn = next_fn

    def iter(self) -> Iterator[str]:
        while True:
            name = None
            if self.next_fn:
                name = self.next_fn(self.sim)
            if name and name in self.sim.agents:
                yield name


class LLMModeratedOrdering(Ordering):
    NAME = "llm_moderated"

    def __init__(self, moderator):
        super().__init__()
        # Fixed types in prototype: moderator must be an Agent object
        self.moderator = moderator
        # Freeze the scheduling candidate set at init time
        self._queue: list[str] = []

    def set_simulation(self, sim):
        self.sim = sim
        self.names: list[str] = list(sim.agents.keys())

    def iter(self) -> Iterator[str]:
        while True:
            if not self._queue:
                self._refill_queue()
            if not self._queue:
                # Fallback to simple sequential if nothing produced
                self._queue.extend(list(self.names))
            yield self._queue.pop(0)

    def post_turn(self, agent_name: str) -> None:
        print(f"Remaining schedule: {self._queue}")
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
            "The schedule is empty now. Please arrange the order of player's action and emit a single "
            '<Action name="schedule_order"><order>["A","B"]</order></Action>. '
            "Do not emit any other action or message."
        )
        mod.add_env_feedback(f"[System] {instruction}")
        # Ask the moderator to take exactly one step with initiative
        action_datas = mod.process(
            self.sim.clients, initiative=True, scene=self.sim.scene
        )
        # Require and execute exactly the scheduling action
        sched = None
        for a in action_datas or []:
            if a and a.get("action") == "schedule_order":
                sched = a
                break
        if sched is None:
            raise ValueError(
                "Moderator must emit schedule_order action during scheduling"
            )
        success, result, summary = self.sim.scene.parse_and_handle_action(
            sched, mod, self.sim
        )
        self.sim.log_event(
            "action_end",
            {
                "agent": mod.name,
                "action": sched,
                "success": success,
                "result": result,
                "summary": summary,
            },
        )

    # Allow schedule action to push into the queue
    def add_to_queue(self, names: list[str]) -> None:
        # Validate and extend
        self._queue.extend([n for n in names if n in self.sim.agents])

    def is_queue_empty(self) -> bool:
        return len(self._queue) == 0


ORDERING_MAP = {
    SequentialOrdering.NAME: SequentialOrdering,
    RandomOrdering.NAME: RandomOrdering,
    AsynchronousOrdering.NAME: AsynchronousOrdering,
    ControlledOrdering.NAME: ControlledOrdering,
    LLMModeratedOrdering.NAME: LLMModeratedOrdering,
}
