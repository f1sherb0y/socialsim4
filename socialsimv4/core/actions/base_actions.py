from socialsimv4.core.action import Action
from socialsimv4.core.event import MessageEvent, SpeakEvent


class SendMessageAction(Action):
    NAME = "send_message"
    DESC = "Post a message to all participants."
    INSTRUCTION = """- To send a message: {"action": "send_message", "message": "[your_message]", "finish": true|false}"""

    def handle(self, action_data, agent, simulator, scene):
        message = action_data.get("message")
        if message:
            agent.log_event("send_message", {"agent": agent.name, "message": message})
            event = MessageEvent(agent.name, message)
            scene.deliver_message(event, agent, simulator)
            return True
        return False


class SkipReplyAction(Action):
    NAME = "skip_reply"
    DESC = "Do nothing this turn."
    INSTRUCTION = """- To skip a reply: {"action": "skip_reply", "finish": true}"""

    def handle(self, action_data, agent, simulator, scene):
        agent.log_event("skip_reply", {"agent": agent.name})
        return True


class SpeakAction(Action):
    NAME = "speak"
    DESC = "Say something in local/proximal chat."
    INSTRUCTION = (
        """- To speak locally: {"action": "speak", "message": "[your_message]", "finish": true|false}"""
    )

    def handle(self, action_data, agent, simulator, scene):
        message = action_data.get("message")
        if message:
            agent.log_event("speak", {"agent": agent.name, "message": message})
            event = SpeakEvent(agent.name, message)
            scene.deliver_message(event, agent, simulator)
            return True
        return False
