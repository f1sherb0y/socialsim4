from event import MessageEvent, PublicEvent


class Action:
    NAME = "base_action"
    INSTRUCTION = ""

    def handle(self, action_data, agent, simulator, scenario):
        raise NotImplementedError


class SendMessageAction(Action):
    NAME = "send_message"
    INSTRUCTION = """- To send a message: {"action": "send_message", "group": "[group_name]", "message": "[your_message]"}"""

    def handle(self, action_data, agent, simulator, scenario):
        group = action_data.get("group", scenario.main_group)
        message = action_data.get("message")
        if message:
            event = MessageEvent(agent.name, group, message)
            formatted = event.to_string(scenario.state.get("time"))
            for a in simulator.agents.values():
                if group in a.joined_groups and a.name != agent.name:
                    a.append_env_message(formatted)
            scenario.log(f"<{agent.name} to {group}> {message}")
            return True
        return False


class SkipReplyAction(Action):
    NAME = "skip_reply"
    INSTRUCTION = """- To skip a reply: {"action": "skip_reply"}"""

    def handle(self, action_data, agent, simulator, scenario):
        scenario.log(f"{agent.name} decided to skip a reply.")
        return True


class ExitGroupchatAction(Action):
    NAME = "exit_groupchat"
    INSTRUCTION = """- To exit a group chat: {"action": "exit_groupchat", "group": "[group_name]"}"""

    def handle(self, action_data, agent, simulator, scenario):
        group = action_data.get("group")
        if group in agent.joined_groups:
            agent.joined_groups.remove(group)
            message = f"{agent.name} has left the group {group}."
            simulator.broadcast(PublicEvent(message))
            scenario.log(message)
            return True
        return False
