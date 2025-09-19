import re

import google.generativeai as genai
from openai import OpenAI

from socialsimv4.api.schemas import LLMConfig


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
            response = self.client.generate_content(contents)
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
            scene = "chat"

        if scene == "council":
            if agent_name.lower() == "host":
                if call_n == 1:
                    action = {"action": "start_voting", "finish": False}
                    thought = "Kick off the voting round as host."
                    plan = "1. Start voting.\n2. Collect votes.\n3. Announce result."
                else:
                    action = {"action": "get_voting_result", "finish": True}
                    thought = "Check if all votes are in and announce the result."
                    plan = "1. Monitor votes. [CURRENT]\n2. Announce result.\n3. Close session."
            else:
                action = {"action": "vote", "vote": "yes", "finish": True}
                thought = "Participate by voting yes."
                plan = "1. Cast vote. [CURRENT]\n2. Provide short rationale."
            plan_update = "no change"

        elif scene == "map":
            if call_n == 1:
                action = {"action": "look_around", "finish": False}
                thought = "Scout surroundings before moving."
                plan = "1. Look around. [CURRENT]\n2. Move to a resource location.\n3. Gather resources.\n4. Rest if needed."
            elif call_n == 2:
                action = {"action": "move_to_location", "location": "farm", "finish": True}
                thought = "Head to the farm for food."
                plan = (
                    "1. Move to farm. [CURRENT]\n2. Gather apples.\n3. Rest if tired."
                )
            elif call_n == 3:
                action = {"action": "gather_resource", "resource": "apple", "amount": 2, "finish": True}
                thought = "Collect some apples to reduce hunger."
                plan = "1. Gather apples. [CURRENT]\n2. Rest if needed."
            else:
                action = {"action": "rest", "finish": True}
                thought = "Recover energy for future tasks."
                plan = "1. Rest. [CURRENT]"
            plan_update = "no change"

        elif scene == "village":
            if call_n == 1:
                action = {"action": "send_message", "message": "Good morning everyone!", "finish": True}
                thought = "Greet others in the village."
                plan = "1. Greet. [CURRENT]\n2. Check needs."
            else:
                action = {"action": "skip_reply", "finish": True}
                thought = "No need to say more now."
                plan = "1. Observe. [CURRENT]"
            plan_update = "no change"

        else:  # simple chat
            if call_n == 1:
                action = {"action": "send_message", "message": f"Hi, I'm {agent_name}.", "finish": True}
                thought = "Introduce myself briefly."
                plan = "1. Say hello. [CURRENT]"
            else:
                action = {"action": "skip_reply", "finish": True}
                thought = "Conversation is stable; skip."
                plan = "1. Skip. [CURRENT]"
            plan_update = "no change"

        # Compose full response
        return (
            f"--- Thoughts ---\n{thought}\n\n"
            f"--- Plan ---\n{plan}\n\n"
            f"--- Action ---\n{json_dumps(action)}\n\n"
            f"--- Plan Update ---\n{plan_update}\n"
        )


def json_dumps(obj):
    # Minimal JSON dumps to avoid importing json here separately from module-global
    import json as _json

    return _json.dumps(obj, ensure_ascii=False)
