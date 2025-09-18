import json
import re

import openai

from socialsimv4.api.config import MAX_REPEAT
from socialsimv4.core.memory import ShortTermMemory

# 假设的最大上下文字符长度（可调整，根据模型实际上下文窗口）
MAX_CONTEXT_CHARS = 100000000
SUMMARY_THRESHOLD = int(MAX_CONTEXT_CHARS * 0.7)  # 70% 阈值


class Agent:
    def __init__(
        self,
        name,
        user_profile,
        style,
        initial_instruction="",
        role_prompt="",
        action_space=[],
        max_repeat=MAX_REPEAT,
        event_handler=None,
        **kwargs,
    ):
        self.name = name
        self.user_profile = user_profile
        self.style = style
        self.initial_instruction = initial_instruction
        self.role_prompt = role_prompt
        self.action_space = action_space
        self.short_memory = ShortTermMemory()
        self.last_history_length = 0
        self.max_repeat = max_repeat
        self.properties = kwargs
        self.log_event = event_handler

    def system_prompt(self, scenario=None):
        base = f"""
You are {self.name}.
You speak in a {self.style} style.

{self.user_profile}

{self.role_prompt}

{scenario.get_scenario_description() if scenario else ""}

{scenario.get_behavior_guidelines() if scenario else ""}

{scenario.get_output_format() if scenario else ""}

Action Space:

{"".join(action.INSTRUCTION for action in self.action_space)}


Here are some examples:
{scenario.get_examples() if scenario else ""}


Initial instruction:
{self.initial_instruction}
"""
        return base

    def call_llm(self, clients, messages, client_name="chat"):
        print(f"LLM call for {self.name} (client: {client_name})...")
        print(f"Messages = {messages}")
        client = clients.get(client_name)
        if not client:
            raise ValueError(f"LLM client '{client_name}' not found.")

        try:
            result = client.chat(messages)
            print(f"LLM API succeeded for {self.name}, response length: {len(result)}\n{result}")
            return result
        except Exception as e:
            print(f"LLM API failed for {self.name}: {e}")
            raise

    def summarize_history(self, client):
        # 构建总结prompt
        history_content = "\n".join(
            [f"[{msg['role']}] {msg['content']}" for msg in self.short_memory.get_all()]
        )
        summary_prompt = f"""
Summarize the following conversation history from {self.name}'s perspective. Be concise but capture key points, opinions, ongoing topics, and important events. Output ONLY as 'Summary: [your summary text]'.

History:
{history_content}
"""

        # 为总结调用LLM（使用简单messages）
        messages = [{"role": "user", "content": summary_prompt}]
        summary_output = self.call_llm(client, messages)

        # 提取总结（假设模型遵循格式）
        summary_match = re.search(r"Summary: (.*)", summary_output, re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()
        else:
            summary = summary_output  # Fallback

        # 替换personal_history：用总结作为新的user消息起点
        self.short_memory.clear()
        self.short_memory.append("user", f"Summary: {summary}")
        print(f"{self.name} summarized history.")

    def _parse_full_response(self, full_response):
        """Extracts thoughts, plan, and the full action block from the response."""
        thoughts_match = re.search(
            r"--- Thoughts ---\s*(.*?)\s*--- Plan ---", full_response, re.DOTALL
        )
        plan_match = re.search(
            r"--- Plan ---\s*(.*?)\s*--- Action ---", full_response, re.DOTALL
        )
        action_match = re.search(r"--- Action ---\s*(.*)", full_response, re.DOTALL)

        thoughts = thoughts_match.group(1).strip() if thoughts_match else ""
        plan = plan_match.group(1).strip() if plan_match else ""
        action = action_match.group(1).strip() if action_match else ""

        return thoughts, plan, action

    def _parse_actions(self, action_block):
        """Parses the action block which should contain a JSON object or a list of JSON objects."""
        action_block = action_block.strip()
        if action_block.startswith("```json"):
            action_block = action_block[7:-3].strip()
        elif action_block.startswith("`"):
            action_block = action_block.strip("`")

        try:
            data = json.loads(action_block)
            if isinstance(data, dict):
                return [data]  # It's a single action
            elif isinstance(data, list):
                return data  # It's a list of actions
            else:
                # Parsed but not a dict or list, not a valid action structure
                return []
        except json.JSONDecodeError:
            # Fallback for malformed JSON. Try to find JSON within the string.
            match = re.search(r"\[.*\]|\{.*\}", action_block, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                    if isinstance(data, dict):
                        return [data]
                    elif isinstance(data, list):
                        return data
                except json.JSONDecodeError:
                    pass  # JSON found but still couldn't parse
            return []

    def process(self, clients, initiative=False, scenario=None):
        print(f"Processing {self.name} (initiative={initiative})")
        current_length = len(self.short_memory)
        if current_length == self.last_history_length and not initiative:
            # 没有新事件，无反应
            print(f"No new messages for {self.name}, skipping")
            return {}

        print(f"{self.name} has {current_length} messages to process")

        # 检查并总结如果需要

        system_prompt = self.system_prompt(scenario)

        # Get history from memory
        ctx = self.short_memory.searilize(dialect="default")
        ctx.insert(0, {"role": "system", "content": system_prompt})
        print(f"{self.name} will send {len(ctx)} messages to LLM, max_repeat={self.max_repeat}")

        action_data = None
        for attempt in range(self.max_repeat):
            try:
                llm_output = self.call_llm(clients, ctx)
                thoughts, plan, action_block = self._parse_full_response(llm_output)
                action_data = self._parse_actions(action_block)

                if not action_data:
                    raise ValueError("No valid action found in LLM output")

                # If parsing succeeds, break
                break
            except (json.JSONDecodeError, ValueError, openai.APIError) as e:
                print(f"Attempt {attempt + 1} failed for {self.name}: {e}")
                if attempt == self.max_repeat - 1:
                    llm_output = "{}"  # Default to empty JSON on final failure
                    action_data = [{}]

        # 原封不动地记录发送的LLM消息到自己的history (即使为空或无效)
        self.short_memory.append("assistant", llm_output)

        # 更新last_history_length（包括新添加的assistant消息）
        self.last_history_length = len(self.short_memory)

        return action_data

    def append_env_message(self, content):
        """Append environmental (user) message to personal_history, merging if last is user."""
        self.short_memory.append("user", content)

    def to_dict(self):
        return {
            "name": self.name,
            "user_profile": self.user_profile,
            "style": self.style,
            "initial_instruction": self.initial_instruction,
            "role_prompt": self.role_prompt,
            "action_space": [action.NAME for action in self.action_space],
            "short_memory": self.short_memory.get_all(),
            "last_history_length": self.last_history_length,
            "max_repeat": self.max_repeat,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data, event_handler=None):
        from .registry import ACTION_SPACE_MAP

        agent = cls(
            name=data["name"],
            user_profile=data["user_profile"],
            style=data["style"],
            initial_instruction=data["initial_instruction"],
            role_prompt=data["role_prompt"],
            action_space=[
                ACTION_SPACE_MAP[action_name] for action_name in data["action_space"]
            ],
            max_repeat=data.get("max_repeat", MAX_REPEAT),
            event_handler=event_handler,
            **data.get("properties", {}),
        )
        agent.short_memory.history = data.get("short_memory", [])
        agent.last_history_length = data.get("last_history_length", 0)
        return agent
