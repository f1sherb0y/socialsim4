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
        return """
Your entire response MUST follow the format specified below. You must generate each of the three sections: Thoughts, Plan, and Action, in every turn.

--- Thoughts ---
// Your internal monologue. Analyze the current situation, your persona, your long-term goals, and the information you have. This section MUST include two parts:
// 1. Re-evaluation: Analyze the latest messages in the conversation. Is your current Plan still relevant? Does it need to be modified? Should you add, remove, or reorder steps? Should you jump to a different step instead of proceeding sequentially? Explicitly state your conclusion about the plan.
// 2. Strategy for This Turn: Based on your re-evaluation, decide on the immediate goal for your current turn.

--- Plan ---
// This is your living strategic document, not a rigid script. It must be updated in every turn based on your `Re-evaluation`. Mark your immediate focus with `[CURRENT]`.
1. [Step 1]
2. [Step 2] [CURRENT]
3. [Step 3]

--- Action ---
// Execute the single action that corresponds to the [CURRENT] step of your plan. This section must contain exactly one action chosen from the Action Space below.
[Formatted action from the Action Space]
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
