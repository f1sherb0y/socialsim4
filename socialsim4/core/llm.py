import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutTimeout

import google.generativeai as genai
from openai import OpenAI

from socialsim4.api.schemas import LLMConfig


class LLMClient:
    def __init__(self, provider: LLMConfig):
        self.provider = provider
        if provider.dialect == "openai":
            self.client = OpenAI(api_key=provider.api_key, base_url=provider.base_url)
        elif provider.dialect == "gemini":
            genai.configure(api_key=provider.api_key)
            self.client = genai.GenerativeModel(provider.model)
        elif provider.dialect == "mock":
            self.client = _MockModel()
        else:
            raise ValueError(f"Unknown LLM provider dialect: {provider.dialect}")
        # Timeout and retry settings (environment-driven defaults)
        self.timeout_s = float(os.getenv("LLM_TIMEOUT_S", "30"))
        self.max_retries = int(os.getenv("LLM_MAX_RETRIES", "2"))
        self.retry_backoff_s = float(os.getenv("LLM_RETRY_BACKOFF_S", "1.0"))

    def _with_timeout_and_retry(self, fn):
        last_err = None
        delay = self.retry_backoff_s
        for attempt in range(self.max_retries + 1):
            try:
                # For OpenAI we'll also pass per-request timeout; for others enforce here
                if self.provider.dialect == "openai":
                    return fn()
                # Run in a thread to enforce timeout
                with ThreadPoolExecutor(max_workers=1) as ex:
                    fut = ex.submit(fn)
                    return fut.result(timeout=self.timeout_s)
            except (FutTimeout, Exception) as e:
                last_err = e
                if attempt < self.max_retries:
                    time.sleep(max(0.0, delay))
                    delay *= 2
                    continue
                raise last_err

    def chat(self, messages):
        if self.provider.dialect == "openai":

            def _do():
                msgs = [
                    {"role": m["role"], "content": m["content"]}
                    for m in messages
                    if m["role"] in ("system", "user", "assistant")
                ]
                resp = self.client.chat.completions.create(
                    model=self.provider.model,
                    messages=msgs,
                    frequency_penalty=self.provider.frequency_penalty,
                    presence_penalty=self.provider.presence_penalty,
                    max_tokens=self.provider.max_tokens,
                    temperature=self.provider.temperature,
                    timeout=self.timeout_s,
                )
                return resp.choices[0].message.content.strip()

            return self._with_timeout_and_retry(_do)
        if self.provider.dialect == "gemini":

            def _do():
                contents = [
                    {
                        "role": ("model" if m["role"] == "assistant" else "user"),
                        "parts": [{"text": m["content"]}],
                    }
                    for m in messages
                    if m["role"] in ("system", "user", "assistant")
                ]
                resp = self.client.generate_content(
                    contents,
                    generation_config={
                        "temperature": self.provider.temperature,
                        "max_output_tokens": self.provider.max_tokens,
                        "top_p": self.provider.top_p,
                        "frequency_penalty": self.provider.frequency_penalty,
                        "presence_penalty": self.provider.presence_penalty,
                    },
                )
                # Some responses may not populate resp.text; extract from candidates if present
                text = ""
                cands = getattr(resp, "candidates", None)
                if cands:
                    first = cands[0] if len(cands) > 0 else None
                    if first is not None:
                        content = getattr(first, "content", None)
                        parts = (
                            getattr(content, "parts", None)
                            if content is not None
                            else None
                        )
                        if parts:
                            text = "".join([getattr(p, "text", "") for p in parts])
                return text.strip()

            return self._with_timeout_and_retry(_do)
        if self.provider.dialect == "mock":

            def _do():
                return self.client.chat(messages)

            return self._with_timeout_and_retry(_do)
        raise ValueError(f"Unknown LLM dialect: {self.provider.dialect}")

    def completion(self, prompt):
        if self.provider.dialect == "openai":
            resp = self.client.completions.create(
                model=self.provider.model,
                prompt=prompt,
                temperature=self.provider.temperature,
                max_tokens=self.provider.max_tokens,
            )
            return resp.choices[0].text.strip()
        if self.provider.dialect == "gemini":
            resp = self.client.generate_content(prompt)
            return resp.text.strip()
        if self.provider.dialect == "mock":
            return ""
        raise ValueError(f"Unknown LLM dialect: {self.provider.dialect}")

    def embedding(self, text):
        if self.provider.dialect == "openai":
            resp = self.client.embeddings.create(model=self.provider.model, input=text)
            return resp.data[0].embedding
        if self.provider.dialect == "gemini":
            return genai.embed_content(model=self.provider.model, content=text)[
                "embedding"
            ]
        if self.provider.dialect == "mock":
            return []
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
        # Extract system content (single string)
        sys_text = next((m["content"] for m in messages if m["role"] == "system"), "")

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
            # Detect scenes by keyword
            if "werewolf" in sys_lower:
                scene = "werewolf"
            elif (
                "dou dizhu" in sys_lower
                or "landlord" in sys_lower
                or "landlord_scene" in sys_lower
            ):
                scene = "landlord"
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

        elif scene == "landlord":
            # Parse latest status to infer phase and current actor
            status = None
            for m in reversed(messages):
                if (
                    m.get("role") == "user"
                    and isinstance(m.get("content"), str)
                    and "Status:" in m.get("content")
                ):
                    status = m["content"]
                    break
            phase = ""
            if status:
                mm = re.search(r"Phase:\s*([a-zA-Z_]+)", status)
                if mm:
                    phase = mm.group(1).strip()
            # Default conservative policy
            act = {"action": "yield"}
            if phase == "bidding":
                # First time: try to call, otherwise pass
                if self.agent_calls[agent_name] == 1:
                    act = {"action": "call_landlord"}
                else:
                    act = {"action": "pass"}
                thought = "Decide whether to call landlord."
                plan = "1. Act in bidding. [CURRENT]"
            elif phase == "doubling":
                act = {"action": "no_double"}
                thought = "Decline doubling."
                plan = "1. Consider doubling. [CURRENT]"
            elif phase == "playing":
                # Try to play the smallest single from the explicit Hand tokens in status
                smallest = None
                if status:
                    hm = re.search(r"Hand:\s*([\w\s]+)", status)
                    if hm:
                        toks = [
                            t
                            for t in hm.group(1).strip().split()
                            if t and t != "(empty)"
                        ]
                        order = [
                            "3",
                            "4",
                            "5",
                            "6",
                            "7",
                            "8",
                            "9",
                            "10",
                            "J",
                            "Q",
                            "K",
                            "A",
                            "2",
                            "SJ",
                            "BJ",
                        ]
                        for r in order:
                            if r in toks:
                                smallest = r
                                break
                if smallest is None:
                    act = {"action": "yield"}
                    thought = "No cards to play."
                    plan = "1. Yield. [CURRENT]"
                else:
                    act = {"action": "play_cards", "cards": smallest}
                    thought = "Try a small single."
                    plan = "1. Play a small single. [CURRENT]"
            else:
                thought = "Wait."
                plan = "1. Yield. [CURRENT]"

            # Render response
            # Produce exact one Action block
            inner = ""
            if act["action"] == "play_cards":
                inner = f"<cards>{act['cards']}</cards>"
            xml = (
                f'<Action name="{act["action"]}">{inner}</Action>'
                if inner
                else f'<Action name="{act["action"]}" />'
            )
            plan_update = "no change"
            return f"--- Thoughts ---\n{thought}\n\n--- Plan ---\n{plan}\n\n--- Action ---\n{xml}\n\n--- Plan Update ---\n{plan_update}"

        else:  # simple chat
            # One sentence per turn: if this is an intra-turn continuation (agent was nudged with 'Continue.'), then yield.
            last_user = None
            for m in reversed(messages):
                if m.get("role") == "user":
                    last_user = (m.get("content") or "").strip()
                    break
            is_continuation = (last_user == "Continue.")
            if is_continuation:
                action = {"action": "yield"}
                thought = "Already spoke this turn; yield."
                plan = "1. Yield. [CURRENT]"
            else:
                # Speak exactly once per turn
                idx = self.agent_calls.get(agent_name, 1)
                action = {
                    "action": "send_message",
                    "message": f"[{idx}] Hello from {agent_name}.",
                }
                thought = "Say one line this turn."
                plan = "1. Speak once. [CURRENT]"
            plan_update = "no change"

        # Compose full response with XML Action
        return (
            f"--- Thoughts ---\n{thought}\n\n"
            f"--- Plan ---\n{plan}\n\n"
            f"--- Action ---\n{action_to_xml(action)}\n\n"
            f"--- Plan Update ---\n{plan_update}\n"
        )


def action_to_xml(a):
    name = a.get("action") or a.get("name") or "yield"
    params = [k for k in a.keys() if k not in ("action", "name")]
    if not params:
        return f'<Action name="{name}" />'
    parts = "".join([f"<{k}>{a[k]}</{k}>" for k in params])
    return f'<Action name="{name}">{parts}</Action>'
