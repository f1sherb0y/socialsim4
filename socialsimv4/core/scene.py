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
Your entire response MUST follow the format below. Always include Thoughts, Plan, and Action. Include Plan Update only when you decide to modify the plan.

Planning guidelines (read carefully):
- Goals: stable end-states. Rarely change; name and describe them briefly.
- Milestones: observable sub-results that indicate progress toward goals.
- Current Focus: the single step you are executing now. Align Action with this.
- Strategy: a brief approach for achieving the goals over time.
- Prefer continuity: preserve unaffected goals/milestones; make the smallest coherent change when adapting to new information. State what stays the same.

--- Thoughts ---
Your internal monologue. Analyze the current situation, your persona, your long-term goals, and the information you have.
Re-evaluation: Compare the latest events with your current plan. Is your plan still relevant? Should you add, remove, or reorder steps? Should you jump to a different step instead of proceeding sequentially? Prefer continuity; preserve unaffected goals and milestones. Explicitly state whether you are keeping or changing the plan and why.
Strategy for This Turn: Based on your re-evaluation, state your immediate objective for this turn and the short rationale for how you will achieve it.

--- Plan ---
// Update the living plan if needed; mark your immediate focus with [CURRENT]. Keep steps concise and executable.
1. [Step 1]
2. [Step 2] [CURRENT]
3. [Step 3]

--- Action ---
// Output exactly one JSON action from the Action Space. No extra text.
{"action": "...", ...}

--- Plan Update ---
// Optional. Include ONLY if you are changing the plan.
// Output either:
// - no change
// - or a JSON object with either a full `replace` or a partial `patch`, plus an optional natural-language `justification`.
// Example (patch):
// {"justification":"...","patch":{"current_focus":{"goal_id":"g1","step":"..."},"notes":"..."}}
// Example (replace):
// {"justification":"...","replace":{"goals":[...],"milestones":[...],"current_focus":{...},"strategy":"...","notes":"..."}}
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
