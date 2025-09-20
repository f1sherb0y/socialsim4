from socialsimv4.core.action import Action
from socialsimv4.core.event import MessageEvent, SpeakEvent


class SendMessageAction(Action):
    NAME = "send_message"
    DESC = "Post a message to all participants."
    INSTRUCTION = """- To send a message:
<Action name=\"send_message\"><message>[your_message]</message></Action>
"""

    def handle(self, action_data, agent, simulator, scene):
        message = action_data.get("message")
        if message:
            # agent.log_event("send_message", {"agent": agent.name, "message": message})
            event = MessageEvent(agent.name, message)
            scene.deliver_message(event, agent, simulator)
            return True
        return False


class YieldAction(Action):
    NAME = "yield"
    DESC = "Yield the floor and end your turn."
    INSTRUCTION = """- To yield the floor:
<Action name=\"yield\" />
"""

    def handle(self, action_data, agent, simulator, scene):
        agent.log_event("yield", {"agent": agent.name})
        return True


class SpeakAction(Action):
    NAME = "speak"
    DESC = "Say something in local/proximal chat."
    INSTRUCTION = """- To speak locally:
<Action name=\"speak\"><message>[your_message]</message></Action>
"""

    def handle(self, action_data, agent, simulator, scene):
        message = action_data.get("message")
        if message:
            agent.log_event("speak", {"agent": agent.name, "message": message})
            event = SpeakEvent(agent.name, message)
            scene.deliver_message(event, agent, simulator)
            return True
        return False
