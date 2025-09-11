from agent import Agent
from event import PublicEvent
from simulator import Simulator


class Scene:
    def __init__(self, name, initial_event):
        self.name = name
        self.initial_event = PublicEvent(initial_event)
        self.state = {}

    def get_scenario_description(self):
        return ""

    def get_behavior_guidelines(self):
        return ""

    def get_output_format(self):
        return """
--- Thoughts ---
Your private thoughts and reasoning about the current situation.

--- Plan ---
Your plan for what to do next.

--- Action ---
The JSON object representing your action. You can perform multiple actions in one turn by outputting an array of action objects.
"""

    def get_examples(self):
        return ""

    def parse_and_handle_action(self, action_data, agent: Agent, simulator: Simulator):
        action_name = action_data.get("action")
        if not action_name:
            return False
        for act in agent.action_space:
            if act.NAME == action_name:
                return act.handle(action_data, agent, simulator, self)
        return False

    def post_round(self, simulator):
        pass

    def is_complete(self):
        return False

    def log(self, message):
        time_str = f"[{self.state.get('time', 0) % 24}:00] "
        print(f"{time_str}{message}")

    def get_agent_status_prompt(self, agent: Agent) -> str:
        """Generates a status prompt for a given agent based on the scene's state."""
        return ""

    def initialize_agent(self, agent: Agent):
        """Initializes an agent with scene-specific properties."""
        pass

    def to_dict(self):
        return {
            "name": self.name,
            "initial_event": self.initial_event.content,
            "state": self.state,
        }

    @classmethod
    def from_dict(cls, data):
        # This is a base class, so we'll just return a generic scene.
        # In a real application, you'd have a factory function that
        # creates the correct scene type based on the data.
        scene = cls(
            name=data["name"],
            initial_event=data["initial_event"],
        )
        scene.state = data["state"]
        return scene
