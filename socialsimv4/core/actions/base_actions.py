from socialsimv4.core.event import MessageEvent, SpeakEvent
from socialsimv4.core.action import Action


class SendMessageAction(Action):
    NAME = "send_message"
    INSTRUCTION = """- To send a message: {"action": "send_message", "message": "[your_message]"}"""

    def handle(self, action_data, agent, simulator, scenario):
        message = action_data.get("message")
        if message:
            agent.log_event("send_message", {"agent": agent.name, "message": message})
            event = MessageEvent(agent.name, message)
            scenario.deliver_message(event, agent, simulator)
            scenario.log(f"<{agent.name}> {message}")
            return True
        return False


class SkipReplyAction(Action):
    NAME = "skip_reply"
    INSTRUCTION = """- To skip a reply: {"action": "skip_reply"}"""

    def handle(self, action_data, agent, simulator, scenario):
        agent.log_event("skip_reply", {"agent": agent.name})
        scenario.log(f"{agent.name} decided to skip a reply.")
        return True


class SpeakAction(Action):
    NAME = "speak"
    INSTRUCTION = """- To speak locally: {"action": "speak", "message": "[your_message]"}"""

    def handle(self, action_data, agent, simulator, scenario):
        message = action_data.get("message")
        if message:
            agent.log_event("speak", {"agent": agent.name, "message": message})
            event = SpeakEvent(agent.name, message)
            scenario.deliver_message(event, agent, simulator)
            scenario.log(f"<{agent.name}> {message}")
            return True
        return False
