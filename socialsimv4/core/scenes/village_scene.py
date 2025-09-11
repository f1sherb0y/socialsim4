from socialsimv4.core.scene import Scene
from socialsimv4.core.agent import Agent
from socialsimv4.core.event import StatusEvent


class VillageScene(Scene):
    def __init__(self, name, main_group, initial_event, time_step=1):
        super().__init__(name, main_group, initial_event)
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

    def post_round(self, simulator):
        self.state["time"] += self.time_step
        for agent in simulator.agents.values():
            agent.hunger = min(100, agent.hunger + 5)
            agent.energy = max(0, agent.energy - 5)
            if agent.hunger >= 80:
                status = f"You are very hungry (hunger: {agent.hunger}). You should eat soon."
                agent.append_env_message(
                    StatusEvent(status).to_string(self.state.get("time") % 24)
                )
                self.log(f"{agent.name} is very hungry!")
            if agent.energy <= 20:
                status = f"You are very tired (energy: {agent.energy}). You should sleep soon."
                agent.append_env_message(
                    StatusEvent(status).to_string(self.state.get("time") % 24)
                )
                self.log(f"{agent.name} is very tired!")

    def get_agent_status_prompt(self, agent: Agent) -> str:
        time_of_day = "day" if self.state.get("time", 0) % 24 < 18 else "night"
        return f"""
--- Status ---
Current position: {agent.position}
Hunger level: {agent.hunger}
Energy level: {agent.energy}
Inventory: {agent.inventory}
Current time: {self.state.get("time", 0)} hours ({time_of_day})
"""
