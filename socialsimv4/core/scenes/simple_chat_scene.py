from socialsimv4.core.actions.base_actions import SendMessageAction, YieldAction
from socialsimv4.core.actions.web_actions import ViewPageAction, WebSearchAction
from socialsimv4.core.scene import Scene


class SimpleChatScene(Scene):
    TYPE = "simple_chat_scene"

    def get_scenario_description(self):
        return """
You are in a chat system with other people. You act like a real person: you only speak when you want to. You decide based on the conversation if it's worth responding.
"""

    def get_behavior_guidelines(self):
        return """
Act like a real person in the chat:
- You have limited patience: if the conversation is boring, repetitive, or drags on too long, you might respond shortly, change the topic, or skip a round.
- Express emotions naturally: show excitement, frustration, agreement, or humor based on what's happening, but stay true to your style (e.g., casual and fun if you're a teen).
- Don't repeat yourself: if you've already shared an opinion, reference it briefly or add a new angle instead of saying the same thing again.
- Respond selectively: like a human, ignore messages that aren't relevant to you, aren't addressed to you, or don't spark interest. Only reply if it feels natural.
- Vary your messages: use varied lengths, casual language, questions, or even emojis if it fits your style. Sometimes greet, joke, or politely disagree.
- Feel fatigue: after many exchanges on the same topic, your responses might get shorter or you might decide to skip.
- Be social: follow basic etiquette like acknowledging others, but act human—not robotic or always agreeable.
- Be open-minded: while you have your own views, you may occasionally shift your opinion slightly if presented with compelling arguments, though it's not necessary.

- You can choose not to send a message.
- If a message is not relevant, not addressed to you, or boring, you might ignore it.
"""

    def get_examples(self):
        return """
--- Thoughts ---
I think I'll say hello to everyone.

--- Plan ---
1. Send a greeting message.

--- Action ---
<Action name="send_message"><message>Hi everyone!</message></Action>

--- Thoughts ---
I want to quickly check recent news about electric cars.

--- Plan ---
1. Search the web for electric car news.
2. Open one promising result to skim content.

--- Action ---
<Action name="web_search"><query>latest news electric cars 2025</query><max_results>3</max_results></Action>
"""

    def get_scene_actions(self, agent):
        """Simple chat supports messaging, yielding, and basic web browsing helpers."""
        return [
            SendMessageAction(),
            YieldAction(),
        ]
