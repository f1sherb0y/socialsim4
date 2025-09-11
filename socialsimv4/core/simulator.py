from event import Event, StatusEvent

from socialsimv4.core.agent import Agent


class Simulator:
    def __init__(
        self, agents, scenario, client, broadcast_initial=True, status_update_interval=1
    ):
        self.agents = {agent.name: agent for agent in agents}  # 用dict便于查找
        self.client = client  # OpenAI客户端
        self.scenario = scenario
        self.main_group = scenario.main_group
        self.round_num = 0
        self.status_update_interval = status_update_interval

        # 让所有智能体加入主组
        for agent in agents:
            agent.joined_groups.add(self.main_group)

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
            "main_group": self.main_group,
            "round_num": self.round_num,
            "status_update_interval": self.status_update_interval,
        }

    @classmethod
    def from_dict(cls, data, client, action_space_map):
        # Note: client is not serialized and must be passed in.
        # action_space_map is also required to reconstruct agents.
        scenario_data = data["scenario"]
        # This is a simplified example. In a real application, you would
        # have a factory function to create the correct scene type.
        from socialsimv4.core.scene import Scene

        scenario = Scene.from_dict(scenario_data)

        agents = [
            Agent.from_dict(agent_data, action_space_map)
            for agent_data in data["agents"].values()
        ]

        simulator = cls(
            agents=agents,
            scenario=scenario,
            client=client,
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
                if not agent or self.main_group not in agent.joined_groups:
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
                action_datas = agent.process(
                    self.client, initiative=is_initiative, scenario=self.scenario
                )
                for action_data in action_datas:
                    if action_data:
                        self.scenario.parse_and_handle_action(action_data, agent, self)

            self.scenario.post_round(self)

            if self.scenario.is_complete():
                print("Scenario complete. Simulation ends.")
                break

            self.round_num += 1
            print(f"--- Round {self.round_num} End ---")

        print("--- Simulation Complete ---")
