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
    ):
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
        if ordering is None:
            ordering: Ordering = SequentialOrdering()
        self.ordering = ordering
        self.ordering.set_simulation(self)
        self.event_queue = Queue()

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

    # ----- Event plumbing: forward to ordering and external handler -----
    def emit_event(self, event_type: str, data: dict):
        # Let ordering observe all events for context-aware scheduling
        self.ordering.on_event(self, event_type, data)
        if self.log_event:
            self.log_event(event_type, data)

    def emit_event_later(self, event_type: str, data: dict):
        self.ordering.on_event(self, event_type, data)
        self.event_queue.put({"type": event_type, "data": data})

    def emit_remaining_events(self):
        while not self.event_queue.empty():
            item = self.event_queue.get()
            if self.log_event:
                self.log_event(item["type"], item["data"])

    def broadcast(self, event: Event):
        sender = event.get_sender()
        time = self.scene.state.get("time")
        formatted = event.to_string(time)

        recipients = []
        for agent in self.agents.values():
            if agent.name != sender:
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

    def to_dict(self):
        return {
            "agents": {name: agent.to_dict() for name, agent in self.agents.items()},
            "scene": self.scene.to_dict(),
            "max_steps_per_turn": self.max_steps_per_turn,
            "ordering": getattr(self.ordering, "NAME", "sequential"),
            "turns": self.turns,
        }

    @classmethod
    def from_dict(cls, data, clients):
        # Note: clients are not serialized and must be passed in.
        scenario_data = data["scene"]
        # This is a simplified example. In a real application, you would
        # have a factory function to create the correct scene type.
        from socialsim4.core.registry import SCENE_MAP

        scene_type = scenario_data["type"]
        scene_class = SCENE_MAP.get(scene_type)
        if not scene_class:
            raise ValueError(f"Unknown scene type: {scene_type}")
        scene = scene_class.from_dict(scenario_data)

        agents = [
            Agent.from_dict(
                agent_data, event_handler=None
            )  # event_handler will be set by SimulationInstance
            for agent_data in data["agents"].values()
        ]

        # Restore ordering if available; fall back to sequential
        ordering_name = data.get("ordering", "sequential")
        ordering_cls = ORDERING_MAP.get(ordering_name, SequentialOrdering)

        simulator = cls(
            agents=agents,
            scene=scene,
            clients=clients,
            broadcast_initial=False,  # Don't rebroadcast initial event
            max_steps_per_turn=data.get("max_steps_per_turn", 5),
            ordering=ordering_cls,
        )
        return simulator

    def run(self, max_turns=1000):
        order_iter = self.ordering.iter()
        turns = 0

        while turns < max_turns:
            if self.scene.is_complete():
                print("Scenario complete. Simulation ends.")
                break

            agent_name = next(order_iter)

            agent = self.agents.get(agent_name)
            if not agent:
                continue

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
            first_step = True
            continue_turn = True
            self.emit_remaining_events()
            while continue_turn and steps < self.max_steps_per_turn:
                self.emit_event(
                    "agent_process_start", {"agent": agent.name, "step": steps + 1}
                )
                action_datas = agent.process(
                    self.clients,
                    initiative=(turns == 0 or not first_step),
                    scene=self.scene,
                )
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
                    self.emit_event(
                        "action_start", {"agent": agent.name, "action": action_data}
                    )
                    success, result, summary = self.scene.parse_and_handle_action(
                        action_data, agent, self
                    )
                    self.emit_event(
                        "action_end",
                        {
                            "agent": agent.name,
                            "action": action_data,
                            "success": success,
                            "result": result,
                            "summary": summary,
                        },
                    )
                    self.emit_remaining_events()
                    if action_data.get("action") == "yield":
                        yielded = True
                        break

                steps += 1
                first_step = False
                if yielded:
                    continue_turn = False

            # Post-turn hooks
            self.scene.post_turn(agent, self)
            self.ordering.post_turn(agent.name)
            turns += 1
            self.turns = turns

        print("--- Simulation Complete ---")
