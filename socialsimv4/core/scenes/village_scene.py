from socialsimv4.core.scene import Scene
from socialsimv4.core.agent import Agent
from socialsimv4.core.event import StatusEvent


class VillageScene(Scene):
    TYPE = "village_scene"
    def __init__(self, name, initial_event, time_step=1):
        super().__init__(name, initial_event)
        self.state["map"] = {
            "home": {
                "type": "residence",
                "description": "Your home where you can sleep and rest.",
            },
            "farm": {"type": "work", "description": "Farm where you can gather food."},
            "market": {
                "type": "social",
                "description": "Market for trading and socializing.",
            },
            "town_hall": {
                "type": "meeting",
                "description": "Town hall for discussions.",
            },
        }
        self.state["time"] = 0  # Simulate time in hours
        self.time_step = time_step

    def get_scenario_description(self):
        return """
You are living in a virtual village. You have needs like hunger and energy, an inventory, and can move between locations on the map.
Locations: home, farm, market, town_hall.
Manage your needs: eat to reduce hunger, sleep to restore energy.
"""

    def get_behavior_guidelines(self):
        return """
Act like a real person in the village:
- Monitor your hunger and energy; act to fulfill needs.
- Move to locations to perform actions (e.g., sleep at home, gather at farm).
- Interact with others at the same location.
- Time passes each round; hunger increases, energy decreases.
"""

    def get_examples(self):
        return """
--- Thoughts ---
I'm getting hungry. I should go to the farm to get some food.

--- Plan ---
1. Move to the farm.
2. Gather some apples.

--- Action ---
--- Move To ---
{"location": "farm"}
"""

    def initialize_agent(self, agent: Agent):
        """Initializes an agent with scene-specific properties."""
        agent.properties["hunger"] = 0
        agent.properties["energy"] = 100
        agent.properties["inventory"] = {}
        agent.properties["position"] = "home"

    def post_round(self, simulator):
        self.state["time"] += self.time_step
        for agent in simulator.agents.values():
            agent.properties["hunger"] = min(100, agent.properties["hunger"] + 5)
            agent.properties["energy"] = max(0, agent.properties["energy"] - 5)
            if agent.properties["hunger"] >= 80:
                status = f"You are very hungry (hunger: {agent.properties['hunger']}). You should eat soon."
                agent.append_env_message(
                    StatusEvent(status).to_string(self.state.get("time") % 24)
                )
                self.log(f"{agent.name} is very hungry!")
            if agent.properties["energy"] <= 20:
                status = f"You are very tired (energy: {agent.properties['energy']}). You should sleep soon."
                agent.append_env_message(
                    StatusEvent(status).to_string(self.state.get("time") % 24)
                )
                self.log(f"{agent.name} is very tired!")

    def get_agent_status_prompt(self, agent: Agent) -> str:
        time_of_day = "day" if self.state.get("time", 0) % 24 < 18 else "night"
        return f"""
--- Status ---
Current position: {agent.properties["position"]}
Hunger level: {agent.properties["hunger"]}
Energy level: {agent.properties["energy"]}
Inventory: {agent.properties["inventory"]}
Current time: {self.state.get("time", 0)} hours ({time_of_day})
"""
