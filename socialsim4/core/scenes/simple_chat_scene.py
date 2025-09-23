from socialsim4.core.actions.base_actions import SendMessageAction, YieldAction
from socialsim4.core.scene import Scene


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

Fact-checking with web tools:
- When news, claims, or factual questions arise, prefer using actions over speculation.
- Use `web_search` to find up-to-date information with a concrete query.
- Optionally follow up with `view_page` to skim a promising source before commenting.
- Summarize findings briefly when you speak.
"""

    def get_examples(self):
        return """
I want to quickly verify a claim by searching the web first.

--- Plan ---
1. Search the web for the claim.

--- Action ---
<Action name="web_search"><query>AI creative writing benchmark human-level 2025 study</query><max_results>3</max_results></Action>

--- Thoughts ---
Open a promising result and skim the content to extract key points.

--- Plan ---
1. View the first promising result.

--- Action ---
<Action name="view_page"><url>https://example.com/article</url><max_chars>2000</max_chars></Action>
"""

    def get_scene_actions(self, agent):
        """Simple chat supports messaging, yielding, and basic web browsing helpers."""
        return [
            SendMessageAction(),
            YieldAction(),
        ]
