from socialsim4.core.action import Action


class ScheduleOrderAction(Action):
    NAME = "schedule_order"
    DESC = "Moderator schedules the next few agents to act using a comma-separated list."
    INSTRUCTION = """
- To schedule the next speakers/actors (moderator only):
<Action name=\"schedule_order\"><order>Alice, Bob, Charlie</order></Action>
"""

    def handle(self, action_data, agent, simulator, scene):
        raw = action_data["order"]
        s = raw.strip()
        names = [x.strip() for x in s.split(",")]

        # No robustness: do not validate membership; let simulator handle unknowns.
        # Just push the list exactly as given into the ordering queue.
        simulator.ordering.add_to_queue(names)

        agent.add_env_feedback("Scheduled order: " + ", ".join(names))
        return True, {"scheduled": names}, f"scheduled {len(names)} agent(s)"
