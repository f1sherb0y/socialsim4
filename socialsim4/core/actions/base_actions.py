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
            simulator.log_event(
                "send_message", {"agent": agent.name, "message": message}
            )
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
        simulator.log_event("yield", {"agent": agent.name})
        return True


class TalkToAction(Action):
    NAME = "talk_to"
    DESC = "Say something to a nearby person by name."
    INSTRUCTION = """- To talk to someone nearby (by name):
<Action name=\"talk_to\"><to>[recipient_name]</to><message>[your_message]</message></Action>
"""

    def handle(self, action_data, agent, simulator, scene):
        to_name = action_data.get("to")
        message = action_data.get("message")
        if not to_name or not message:
            agent.append_env_message("Provide 'to' (name) and 'message'.")
            return False

        target = simulator.agents.get(to_name)
        if not target:
            agent.append_env_message(f"No such person: {to_name}.")
            return False

        # Range check for scenes with spatial chat
        in_range = True
        try:
            sxy = agent.properties.get("map_xy")
            txy = target.properties.get("map_xy")
            chat_range = getattr(scene, "chat_range", None)
            if sxy and txy and chat_range is not None:
                dist = abs(sxy[0] - txy[0]) + abs(sxy[1] - txy[1])
                in_range = dist <= chat_range
        except Exception:
            in_range = True

        if not in_range:
            agent.append_env_message(f"{to_name} is too far to talk to.")
            return False

        event = SpeakEvent(agent.name, message)
        # Sender always sees their own speech
        agent.append_env_message(event.to_string(scene.state.get("time")))
        # Deliver only to the target
        target.append_env_message(event.to_string(scene.state.get("time")))
        simulator.record_log(
            event.to_string(scene.state.get("time")),
            sender=agent.name,
            recipients=[to_name],
            kind=event.__class__.__name__,
        )
        return True
