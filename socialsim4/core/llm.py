import re

import google.generativeai as genai
from openai import OpenAI

from socialsim4.api.schemas import LLMConfig


class LLMClient:
    def __init__(self, provider: LLMConfig):
        self.provider = provider
        if self.provider.dialect == "openai":
            self.client = OpenAI(
                api_key=self.provider.api_key,
                base_url=self.provider.base_url,
            )
        elif self.provider.dialect == "gemini":
            genai.configure(api_key=self.provider.api_key)
            self.client = genai.GenerativeModel(self.provider.model)
        elif self.provider.dialect == "mock":
            self.client = _MockModel()
        else:
            raise ValueError(f"Unknown LLM provider dialect: {self.provider.dialect}")

    def chat(self, messages):
        if self.provider.dialect == "openai":
            openai_messages = []
            for msg in messages:
                role = msg.get("role")
                if role not in ["system", "user", "assistant"]:
                    continue

                # Handle system messages that might have 'content' instead of 'parts'
                if role == "system" and "content" in msg:
                    openai_messages.append(
                        {"role": "system", "content": msg["content"]}
                    )
                    continue

                content_parts = []
                for part in msg.get("parts", []):
                    if isinstance(part, str):
                        content_parts.append({"type": "text", "text": part})
                    elif isinstance(part, dict) and "inline_data" in part:
                        inline_data = part["inline_data"]
                        mime_type = inline_data.get("mime_type")
                        data = inline_data.get("data")
                        if mime_type and data:
                            content_parts.append(
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime_type};base64,{data}"
                                    },
                                }
                            )

                if content_parts:
                    openai_messages.append({"role": role, "content": content_parts})

            response = self.client.chat.completions.create(
                model=self.provider.model,
                messages=openai_messages,
                frequency_penalty=self.provider.frequency_penalty,
                presence_penalty=self.provider.presence_penalty,
                max_tokens=self.provider.max_tokens,
                temperature=self.provider.temperature,
            )
            return response.choices[0].message.content.strip()
        elif self.provider.dialect == "gemini":
            # Map our internal messages (role + parts/content) to Gemini's expected contents
            contents = []
            for msg in messages:
                role = msg.get("role")
                if role not in ["system", "user", "assistant"]:
                    continue
                gem_role = "model" if role == "assistant" else "user"
                parts = []
                # Preferred path: parts array (our ShortTermMemory.serialize builds this)
                if "parts" in msg:
                    for part in msg.get("parts", []):
                        if isinstance(part, str):
                            parts.append({"text": part})
                        elif isinstance(part, dict) and "inline_data" in part:
                            inline_data = part["inline_data"]
                            mime_type = inline_data.get("mime_type")
                            data = inline_data.get("data")
                            if mime_type and data:
                                parts.append(
                                    {
                                        "inline_data": {
                                            "mime_type": mime_type,
                                            "data": data,
                                        }
                                    }
                                )
                # Fallback path: single content string/list (e.g., system message we insert)
                if not parts and "content" in msg:
                    content = msg["content"]
                    if isinstance(content, str):
                        parts.append({"text": content})
                    elif isinstance(content, list):
                        for p in content:
                            if isinstance(p, dict) and "text" in p:
                                parts.append({"text": p["text"]})
                if parts:
                    contents.append({"role": gem_role, "parts": parts})
            response = self.client.generate_content(
                contents,
                generation_config={
                    "temperature": self.provider.temperature,
                    "max_output_tokens": self.provider.max_tokens,
                    "top_p": self.provider.top_p,
                    "frequency_penalty": self.provider.frequency_penalty,
                    "presence_penalty": self.provider.presence_penalty,
                },
            )
            return response.text.strip()
        elif self.provider.dialect == "mock":
            return self.client.chat(messages)
        else:
            raise ValueError(f"Unknown LLM dialect: {self.provider.dialect}")

    def completion(self, prompt):
        if self.provider.dialect == "openai":
            response = self.client.completions.create(
                model=self.provider.model,
                prompt=prompt,
                temperature=self.provider.temperature,
                max_tokens=self.provider.max_tokens,
            )
            return response.choices[0].text.strip()
        elif self.provider.dialect == "gemini":
            response = self.client.generate_content(prompt)
            return response.text.strip()
        elif self.provider.dialect == "mock":
            # Not used for mock
            return ""
        else:
            raise ValueError(f"Unknown LLM dialect: {self.provider.dialect}")

    def embedding(self, text):
        if self.provider.dialect == "openai":
            response = self.client.embeddings.create(
                model=self.provider.model,
                input=text,
            )
            return response.data[0].embedding
        elif self.provider.dialect == "gemini":
            return genai.embed_content(
                model=self.provider.model,
                content=text,
            )["embedding"]
        elif self.provider.dialect == "mock":
            return []
        else:
            raise ValueError(f"Unknown LLM dialect: {self.provider.dialect}")


def create_llm_client(provider: LLMConfig):
    return LLMClient(provider)


class _MockModel:
    """Deterministic local stub for offline testing.
    Produces valid Thoughts/Plan/Action and optional Plan Update, with simple heuristics.
    """

    def __init__(self):
        self.agent_calls = {}

    def chat(self, messages):
        # Extract system content
        sys = next(
            (m.get("content") for m in messages if m.get("role") == "system"), ""
        )
        if isinstance(sys, list):
            # OpenAI format might be a list of dicts; flatten to text
            sys_text = "\n".join(x.get("text", "") for x in sys if isinstance(x, dict))
        else:
            sys_text = sys or ""

        # Identify agent name
        m = re.search(r"You are\s+([^\n\.]+)", sys_text)
        agent_name = m.group(1).strip() if m else "Agent"
        self.agent_calls[agent_name] = self.agent_calls.get(agent_name, 0) + 1
        call_n = self.agent_calls[agent_name]

        sys_lower = sys_text.lower()

        # Pick scene by keywords in system prompt
        if "grid-based virtual village" in sys_lower:
            scene = "map"
        elif "vote" in sys_lower or "voting" in sys_lower:
            scene = "council"
        elif "you are living in a virtual village" in sys_lower:
            scene = "village"
        else:
            # Detect werewolf scene by keyword
            if "werewolf" in sys_lower:
                scene = "werewolf"
            else:
                scene = "chat"

        if scene == "council":
            if agent_name.lower() == "host":
                if call_n == 1:
                    action = {
                        "action": "send_message",
                        "message": "Good morning, council.",
                    }
                    thought = "Open the session briefly."
                    plan = "1. Greet. [CURRENT]"
                else:
                    action = {"action": "yield"}
                    thought = "Yield the floor for members to respond."
                    plan = "1. Yield. [CURRENT]"
            else:
                if call_n == 1:
                    action = {
                        "action": "send_message",
                        "message": "I support moving forward.",
                    }
                    thought = "Make a brief opening remark."
                    plan = "1. Remark. [CURRENT]"
                else:
                    action = {"action": "yield"}
                    thought = "No further comment now."
                    plan = "1. Yield. [CURRENT]"
            plan_update = "no change"

        elif scene == "map":
            if call_n == 1:
                action = {"action": "look_around"}
                thought = "Scout surroundings before moving."
                plan = "1. Look around. [CURRENT]"
            else:
                action = {"action": "yield"}
                thought = "Pause to let others act."
                plan = "1. Yield. [CURRENT]"
            plan_update = "no change"

        elif scene == "village":
            if call_n == 1:
                action = {"action": "send_message", "message": "Good morning everyone!"}
                thought = "Greet others in the village."
                plan = "1. Greet. [CURRENT]"
            else:
                action = {"action": "yield"}
                thought = "No need to say more now."
                plan = "1. Yield. [CURRENT]"
            plan_update = "no change"

        elif scene == "werewolf":
            # Heuristic role detection from system profile
            role = "villager"
            if "you are the seer" in sys_lower or "you are seer" in sys_lower:
                role = "seer"
            elif "you are the witch" in sys_lower or "you are witch" in sys_lower:
                role = "witch"
            elif "you are a werewolf" in sys_lower or "you are werewolf" in sys_lower:
                role = "werewolf"

            # Use fixed names from demo to make actions meaningful
            default_targets = ["Pia", "Taro", "Elena", "Bram", "Ronan", "Mira"]

            def pick_other(exclude):
                for n in default_targets:
                    if n != exclude:
                        return n
                return "Pia"

            if call_n == 1:
                if role == "werewolf":
                    action = {"action": "night_kill", "target": "Pia"}
                    thought = "Coordinate a night kill discreetly."
                    plan = "1. Night kill. [CURRENT]"
                elif role == "seer":
                    action = {"action": "inspect", "target": "Ronan"}
                    thought = "Inspect a likely suspect."
                    plan = "1. Inspect. [CURRENT]"
                elif role == "witch":
                    action = {"action": "witch_save"}
                    thought = "Prepare to save tonight's victim."
                    plan = "1. Save. [CURRENT]"
                else:  # villager
                    action = {"action": "yield"}
                    thought = "Nothing to do at night."
                    plan = "1. Wait. [CURRENT]"
            else:
                # Daytime: cast a vote
                target = "Ronan" if role != "werewolf" else "Elena"
                action = {"action": "vote_lynch", "target": target}
                thought = "Participate in the day vote."
                plan = "1. Vote. [CURRENT]"

            plan_update = "no change"

        else:  # simple chat
            if call_n == 1:
                action = {"action": "send_message", "message": f"Hi, I'm {agent_name}."}
                thought = "Introduce myself briefly."
                plan = "1. Say hello. [CURRENT]"
            else:
                action = {"action": "yield"}
                thought = "Conversation is stable; yield."
                plan = "1. Yield. [CURRENT]"
            plan_update = "no change"

        # Compose full response with XML Action
        return (
            f"--- Thoughts ---\n{thought}\n\n"
            f"--- Plan ---\n{plan}\n\n"
            f"--- Action ---\n{action_to_xml(action)}\n\n"
            f"--- Plan Update ---\n{plan_update}\n"
        )


def action_to_xml(a):
    # Convert a simple dict action to XML string for the mock model
    if not isinstance(a, dict):
        return '<Action name="yield"></Action>'
    name = a.get("action") or a.get("name") or "yield"
    params = [k for k in a.keys() if k not in ("action", "name")]
    if not params:
        return f'<Action name="{name}" />'
    parts = "".join([f"<{k}>{a[k]}</{k}>" for k in params])
    return f'<Action name="{name}">{parts}</Action>'
