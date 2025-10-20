from copy import deepcopy
from queue import Queue
from typing import Callable, List, Optional

from socialsim4.core.agent import Agent
from socialsim4.core.event import Event, StatusEvent
from socialsim4.core.ordering import ORDERING_MAP, Ordering, SequentialOrdering

# from socialsim4.core.scene import Scene


class Simulator:
    def __init__(
        self,
        agents: List[Agent],
        scene,
        clients,
        broadcast_initial=True,
        max_steps_per_turn=5,
        ordering: Optional[Ordering] = None,
        event_handler: Callable[[str, dict], None] = None,
        emotion_enabled: bool = False,
    ):
        self.started = False
        self.log_event = event_handler

        for agent in agents:
            agent.log_event = self.log_event

        self.agents = {agent.name: agent for agent in agents}  # 用dict便于查找
        self.clients = clients  # Dictionary of LLM clients
        self.scene = scene
        # Track total turns processed (no round concept)
        self.turns = 0
        # No round concept: keep only per-turn limits
        self.max_steps_per_turn = max_steps_per_turn
        # Build ordering (class or instance); keep it simple
        self.ordering = ordering
        self.ordering.set_simulation(self)
        self.event_queue = Queue()
        self.order_iter = self.ordering.iter()
        self.emotion_enabled = emotion_enabled

        # Initialize agents for the scene if it's a new simulation
        if broadcast_initial:
            for agent in agents:
                self.scene.initialize_agent(agent)
                # Append scene-specific actions without modifying base action spaces here
                scene_actions = self.scene.get_scene_actions(agent) or []
                existing = {getattr(a, "NAME", None) for a in agent.action_space}
                for act in scene_actions:
                    name = getattr(act, "NAME", None)
                    if name and name not in existing:
                        agent.action_space.append(act)

        if broadcast_initial:
            self.broadcast(self.scene.initial_event)

        # Only run scene.pre_run for fresh simulations; skip during clones/deserialization
        if broadcast_initial:
            self.scene.pre_run(self)
        self.started = True

    # ----- Event plumbing: forward to ordering and external handler -----
    def emit_event(self, event_type: str, data: dict):
        # Let ordering observe all events for context-aware scheduling
        if self.log_event:
            self.log_event(event_type, data)
        if self.started:
            self.ordering.on_event(self, event_type, data)

    def emit_event_later(self, event_type: str, data: dict):
        self.event_queue.put({"type": event_type, "data": data})

    def emit_remaining_events(self):
        while not self.event_queue.empty():
            item = self.event_queue.get()
            self.emit_event(item["type"], item["data"])

    def broadcast(self, event: Event, receivers: Optional[List[str]] = None):
        sender = event.get_sender()
        time = self.scene.state.get("time")
        formatted = event.to_string(time)

        recipients = []
        for agent in self.agents.values():
            if agent.name != sender and (receivers is None or agent.name in receivers):
                agent.add_env_feedback(formatted)
                recipients.append(agent.name)

        # Timeline: keep minimal
        self.emit_event_later(
            "system_broadcast",
            {
                "time": time,
                "type": event.__class__.__name__,
                "sender": sender,
                "recipients": recipients,
                "text": event.to_string(),
            },
        )

    # No external turn requests in this prototype; agents are isolated from simulator

    # Clear serialization with deep-copy semantics
    def serialize(self):
        ord_state = self.ordering.serialize()
        snap = {
            "agents": {name: agent.serialize() for name, agent in self.agents.items()},
            "scene": self.scene.serialize(),
            "max_steps_per_turn": int(self.max_steps_per_turn),
            "ordering": getattr(self.ordering, "NAME", "sequential"),
            "ordering_state": ord_state,
            # Serialize pending event queue as a list of items
            "event_queue": list(self.event_queue.queue),
            "turns": int(self.turns),
            "emotion_enabled": self.emotion_enabled,
        }
        return deepcopy(snap)

    @classmethod
    def deserialize(cls, data, clients, log_handler=None):
        data = deepcopy(data)
        # Note: clients are not serialized and must be passed in.
        scenario_data = data["scene"]
        from socialsim4.core.registry import SCENE_MAP

        scene_type = scenario_data["type"]
        scene_class = SCENE_MAP.get(scene_type)
        if not scene_class:
            raise ValueError(f"Unknown scene type: {scene_type}")
        scene = scene_class.deserialize(scenario_data)

        agents = [Agent.deserialize(agent_data, event_handler=None) for agent_data in data["agents"].values()]

        # Restore ordering if available; fall back to sequential
        ordering_name = data.get("ordering", "sequential")
        ordering_state = data.get("ordering_state")
        ordering_cls = ORDERING_MAP.get(ordering_name, SequentialOrdering)
        # Construct ordering, preserving state if available
        if ordering_name == "cycled":
            names = []
            if ordering_state and isinstance(ordering_state, dict):
                names = list(ordering_state.get("names", []))
            ordering = ordering_cls(names)
        elif ordering_name == "controlled":
            # Rebuild with a scene-aware next_fn to preserve behavior after deserialization
            def _next(sim):
                return sim.scene.get_controlled_next(sim)

            ordering = ordering_cls(next_fn=_next)
        else:
            ordering = ordering_cls()

        simulator = cls(
            agents=agents,
            scene=scene,
            clients=clients,
            broadcast_initial=False,  # Don't rebroadcast initial event
            max_steps_per_turn=data.get("max_steps_per_turn", 5),
            ordering=ordering,
            event_handler=log_handler,
            emotion_enabled=data["emotion_enabled"],
        )
        # Apply ordering state if provided
        simulator.ordering.deserialize(ordering_state)
        simulator.order_iter = simulator.ordering.iter()
        # Restore pending event queue contents
        pending = data.get("event_queue") or []
        if pending:
            q = Queue()
            for item in pending:
                q.put(item)
            simulator.event_queue = q
        return simulator

    def run(self, max_turns=1000):
        turns = 0
        print(f"Running for {max_turns} turns.")

        while turns < max_turns:
            if self.scene.is_complete():
                print("Scenario complete. Simulation ends.")
                break

            agent_name = next(self.order_iter)

            agent = self.agents.get(agent_name)
            print(f"Turn {turns}: {agent_name}")

            if not agent:
                continue

            print("Running turn..")
            # Optional: provide a status prompt at the start of each turn
            status_prompt = self.scene.get_agent_status_prompt(agent)
            if status_prompt:
                evt = StatusEvent(status_prompt)
                text = evt.to_string(self.scene.state.get("time"))
                agent.add_env_feedback(text)

            # Skip turn based on scene rule
            if self.scene.should_skip_turn(agent, self):
                print(f"Skipping turn for {agent.name} as per scene rules.")
                self.scene.post_turn(agent, self)
                self.ordering.post_turn(agent.name)
                turns += 1
                continue

            # Intra-turn loop (bounded by global cap)
            steps = 0
            continue_turn = True
            self.emit_remaining_events()

            print(2)

            while continue_turn and steps < self.max_steps_per_turn:
                try:
                    print(3)
                    self.emit_event("agent_process_start", {"agent": agent.name, "step": steps + 1})
                    action_datas = agent.process(
                        self.clients,
                        initiative=False,
                        scene=self.scene,
                    )
                    print(4)
                    self.emit_event(
                        "agent_process_end",
                        {
                            "agent": agent.name,
                            "step": steps + 1,
                            "actions": action_datas,
                        },
                    )

                    if not action_datas:
                        break

                    yielded = False
                    for action_data in action_datas:
                        if not action_data:
                            continue
                        self.emit_event("action_start", {"agent": agent.name, "action": action_data})
                        success, result, summary, meta, pass_control = self.scene.parse_and_handle_action(action_data, agent, self)
                        self.emit_event(
                            "action_end",
                            {
                                "agent": agent.name,
                                "action": action_data,
                                "success": success,
                                "result": result,
                                "summary": summary,
                                "pass_control": bool(pass_control),
                            },
                        )
                        self.emit_remaining_events()
                        if bool(pass_control):
                            yielded = True
                            break
                except Exception as e:
                    print(f"Exception: {e}")

                steps += 1
                if yielded:
                    continue_turn = False

            # Post-turn hooks
            self.scene.post_turn(agent, self)
            self.emit_remaining_events()
            self.ordering.post_turn(agent.name)
            turns += 1
            self.turns = turns
