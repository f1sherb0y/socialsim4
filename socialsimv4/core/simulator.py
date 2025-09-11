import json
from socialsimv4.core.event import Event, StatusEvent
from socialsimv4.core.agent import Agent


class Simulator:
    def __init__(
        self, agents, scenario, clients, broadcast_initial=True, status_update_interval=1, event_handler=None
    ):
        self.log_event = event_handler
        
        for agent in agents:
            agent.log_event = self.log_event

        self.agents = {agent.name: agent for agent in agents}  # 用dict便于查找
        self.clients = clients  # Dictionary of LLM clients
        self.scenario = scenario
        self.round_num = 0
        self.status_update_interval = status_update_interval

        # Initialize agents for the scene if it's a new simulation
        if broadcast_initial:
            for agent in agents:
                self.scenario.initialize_agent(agent)

        # 初始化所有agent的personal_history：添加初始事件作为user role if flag is True
        if broadcast_initial:
            self.broadcast(self.scenario.initial_event)

    def broadcast(self, event: Event):
        sender = event.get_sender()
        time = self.scenario.state.get("time")
        formatted = event.to_string(time)

        for agent in self.agents.values():
            # Since we removed joined_groups, we assume all agents are in the main group
            if agent.name != sender:
                agent.append_env_message(formatted)

    def to_dict(self):
        return {
            "agents": {name: agent.to_dict() for name, agent in self.agents.items()},
            "scenario": self.scenario.to_dict(),
            "round_num": self.round_num,
            "status_update_interval": self.status_update_interval,
        }

    @classmethod
    def from_dict(cls, data, clients):
        # Note: clients are not serialized and must be passed in.
        scenario_data = data["scenario"]
        # This is a simplified example. In a real application, you would
        # have a factory function to create the correct scene type.
        from socialsimv4.core.registry import SCENE_MAP
        scene_type = scenario_data.get("type", "map_scene")
        scene_class = SCENE_MAP.get(scene_type)
        if not scene_class:
            raise ValueError(f"Unknown scene type: {scene_type}")
        scenario = scene_class.from_dict(scenario_data)

        agents = [
            Agent.from_dict(agent_data, event_handler=None) # event_handler will be set by SimulationInstance
            for agent_data in data["agents"].values()
        ]

        simulator = cls(
            agents=agents,
            scenario=scenario,
            clients=clients,
            broadcast_initial=False,  # Don't rebroadcast initial event
            status_update_interval=data["status_update_interval"],
        )
        simulator.round_num = data["round_num"]
        return simulator

    def run(self, max_rounds=50):
        agent_order = list(self.agents.keys())  # 动态顺序，基于agents dict keys

        print("--- Initialization ---")

        self.round_num = 0

        while self.round_num < max_rounds:
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
                    status_prompt = self.scenario.get_agent_status_prompt(agent)
                    if status_prompt:
                        agent.append_env_message(status_prompt)

                # 调用process. agent内部的逻辑会判断是否有新消息，决定是否调用LLM
                self.log_event("agent_process_start", {"agent": agent.name})
                action_datas = agent.process(
                    self.clients, initiative=is_initiative, scenario=self.scenario
                )
                self.log_event("agent_process_end", {"agent": agent.name, "actions": action_datas})

                for action_data in action_datas:
                    if action_data:
                        self.log_event("action_start", {"agent": agent.name, "action": action_data})
                        self.scenario.parse_and_handle_action(action_data, agent, self)
                        self.log_event("action_end", {"agent": agent.name, "action": action_data})

            self.scenario.post_round(self)

            if self.scenario.is_complete():
                print("Scenario complete. Simulation ends.")
                break

            self.round_num += 1
            print(f"--- Round {self.round_num} End ---")

        print("--- Simulation Complete ---")
