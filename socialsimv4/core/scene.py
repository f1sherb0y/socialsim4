from socialsimv4.core.agent import Agent
from socialsimv4.core.event import PublicEvent
from socialsimv4.core.simulator import Simulator


class Scene:
    TYPE = "scene"

    def __init__(self, name, initial_event):
        self.name = name
        self.initial_event = PublicEvent(initial_event)
        self.state = {}

    def get_scenario_description(self):
        return ""

    def get_behavior_guidelines(self):
        return ""

    def get_output_format(self):
        # Format instructions are now injected by Agent.get_output_format().
        # Scenes can override this if they need scene-specific format additions.
        return ""

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

    def deliver_message(self, event, sender: Agent, simulator: Simulator):
        """Deliver a chat message event. Default behavior is global broadcast
        to all agents except the sender. Scenes can override to restrict scope
        (e.g., proximity-based chat in map scenes).
        """
        simulator.broadcast(event)

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

    def get_scene_actions(self, agent: Agent):
        """Return a list of Action instances this scene enables for the agent.
        Default: no additional actions.
        """
        return []

    def to_dict(self):
        return {
            "name": self.name,
            "initial_event": self.initial_event.content,
            "state": self.state,
            "type": getattr(self, "TYPE", "scene"),
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
        scene.state = data.get("state", dict())
        return scene
