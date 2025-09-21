import json

from socialsimv4.core.agent import Agent
from socialsimv4.core.event import Event, StatusEvent


class Simulator:
    def __init__(
        self,
        agents,
        scene,
        clients,
        broadcast_initial=True,
        status_update_interval=1,
        max_steps_per_turn=5,
        event_handler=None,
    ):
        self.log_event = event_handler

        for agent in agents:
            agent.log_event = self.log_event

        self.agents = {agent.name: agent for agent in agents}  # 用dict便于查找
        self.clients = clients  # Dictionary of LLM clients
        self.scene = scene
        self.round_num = 0
        self.event_log = []  # chronological list of events (dict records)
        self.status_update_interval = status_update_interval
        self.max_steps_per_turn = max_steps_per_turn

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

        # 初始化所有agent的personal_history：添加初始事件作为user role if flag is True
        if broadcast_initial:
            self.broadcast(self.scene.initial_event)

    def record_event(self, event: Event, recipients=None):
        """Record an event with time, type, text, sender, recipients.
        recipients: list of agent names or None (means broadcast to all except sender).
        """
        time = self.scene.state.get("time")
        try:
            text = event.to_string(time)
        except Exception:
            text = str(event)
        record = {
            "time": time,
            "type": event.__class__.__name__,
            "sender": event.get_sender() if hasattr(event, "get_sender") else None,
            "recipients": recipients,  # None implies broadcast
            "text": text,
        }
        self.event_log.append(record)
        if self.log_event:
            self.log_event("event_recorded", record)

    def record_log(self, text: str, sender: str = None, recipients=None, kind: str = "log"):
        """Record a non-world, informational transcript line without using Event.
        Intended for private notes like web searches or page views.
        """
        record = {
            "time": self.scene.state.get("time"),
            "type": kind,
            "sender": sender,
            "recipients": recipients,
            "text": text,
        }
        self.event_log.append(record)
        if self.log_event:
            self.log_event("log_recorded", record)

    def broadcast(self, event: Event):
        sender = event.get_sender()
        time = self.scene.state.get("time")
        formatted = event.to_string(time)

        recipients = []
        for agent in self.agents.values():
            # Since we removed joined_groups, we assume all agents are in the main group
            if agent.name != sender:
                agent.append_env_message(formatted)
                recipients.append(agent.name)
        # Record broadcast
        self.record_event(event, recipients=recipients)

    def to_dict(self):
        return {
            "agents": {name: agent.to_dict() for name, agent in self.agents.items()},
            "scene": self.scene.to_dict(),
            "round_num": self.round_num,
            "status_update_interval": self.status_update_interval,
            "max_steps_per_turn": self.max_steps_per_turn,
            "event_log": self.event_log,
        }

    @classmethod
    def from_dict(cls, data, clients):
        # Note: clients are not serialized and must be passed in.
        scenario_data = data["scene"]
        # This is a simplified example. In a real application, you would
        # have a factory function to create the correct scene type.
        from socialsimv4.core.registry import SCENE_MAP

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

        simulator = cls(
            agents=agents,
            scene=scene,
            clients=clients,
            broadcast_initial=False,  # Don't rebroadcast initial event
            status_update_interval=data.get("status_update_interval", 1),
            max_steps_per_turn=data.get("max_steps_per_turn", 5),
        )
        simulator.round_num = data["round_num"]
        simulator.event_log = data.get("event_log", [])
        return simulator

    def get_transcript(self) -> str:
        """Return a plain-text transcript of all recorded events so far."""
        return "\n".join(record.get("text", "") for record in self.event_log)

    def run(self, num_rounds=50):
        agent_order = list(self.agents.keys())  # 动态顺序，基于agents dict keys

        print("--- Initialization ---")
        round = 0

        while round < num_rounds:
            # 每一轮都按固定顺序处理所有agent
            for agent_name in agent_order:
                agent = self.agents.get(agent_name)
                if not agent:
                    continue

                # First agent (Host) in first round has initiative
                is_initiative = self.round_num == 0 and agent_name == agent_order[0]

                # Add status update before processing
                if (
                    self.round_num > 0
                    and self.round_num % self.status_update_interval == 0
                ):
                    status_prompt = self.scene.get_agent_status_prompt(agent)
                    if status_prompt:
                        # Wrap as a status event for logging
                        evt = StatusEvent(status_prompt)
                        agent.append_env_message(
                            evt.to_string(self.scene.state.get("time"))
                        )
                        self.record_event(evt, recipients=[agent.name])

                # Multi-step per-turn loop (agent may act multiple times until yield)
                steps = 0
                first_step = True
                continue_turn = True
                while continue_turn and steps < self.max_steps_per_turn:
                    # 调用process. agent内部的逻辑会判断是否有新消息，决定是否调用LLM
                    self.log_event(
                        "agent_process_start", {"agent": agent.name, "step": steps + 1}
                    )
                    action_datas = agent.process(
                        self.clients,
                        initiative=(is_initiative or not first_step),
                        scene=self.scene,
                    )
                    self.log_event(
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
                    any_handled = False
                    for action_data in action_datas:
                        if not action_data:
                            continue
                        self.log_event(
                            "action_start", {"agent": agent.name, "action": action_data}
                        )
                        self.scene.parse_and_handle_action(action_data, agent, self)
                        self.log_event(
                            "action_end", {"agent": agent.name, "action": action_data}
                        )
                        any_handled = True
                        # Stop if agent yields the floor
                        if action_data.get("action") == "yield":
                            yielded = True
                            break

                    steps += 1
                    first_step = False
                    if yielded or not any_handled:
                        continue_turn = False

            self.scene.post_round(self)

            if self.scene.is_complete():
                print("Scenario complete. Simulation ends.")
                break

            self.round_num += 1
            round += 1
            print(f"--- Round {self.round_num} End ---")

        print("--- Simulation Complete ---")
