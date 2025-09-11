import json
import re

import openai
from memory import ShortTermMemory

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
        max_repeat=3,
        position=None,
        hunger=0,
        energy=100,
        inventory=None,
        map_position=None,
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
        self.position = position or "home"
        self.hunger = hunger
        self.energy = energy
        self.inventory = inventory or {}
        self.joined_groups = set()  # 添加joined_groups属性
        self.map_position = map_position or position or "village_center"  # 地图位置

    def system_prompt(self, scenario=None):
        base = f"""
{self.user_profile}

{self.role_prompt}

{scenario.get_scenario_description() if scenario else ""}

{scenario.get_behavior_guidelines() if scenario else ""}

{scenario.get_output_format() if scenario else ""}

{"".join(action.INSTRUCTION for action in self.action_space)}

- Respond in character: keep it {self.style}.

{scenario.get_examples() if scenario else ""}

{self.initial_instruction}
"""
        return base

    def call_llm(self, client, messages):
        print(f"🤖 {self.name} 正在调用LLM API...")
        try:
            response = client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=messages,
                temperature=0.7,
            )
            result = response.choices[0].message.content.strip()
            print(f"✅ {self.name} API调用成功，响应长度: {len(result)} 字符")
            return result
        except Exception as e:
            print(f"❌ {self.name} API调用失败: {e}")
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
        """Extracts a list of actions from the action block."""
        actions = []
        # Pattern to find all --- Action Type --- sections
        pattern = r"--- (.+?) ---\s*(.*?)(?=\n--- |\Z)"
        matches = re.findall(pattern, action_block, re.DOTALL)
        
        for match in matches:
            action_type = match[0].strip().lower().replace(" ", "_")
            action_content = match[1].strip()
            actions.append({"action": action_type, "content": action_content})
            
        return actions

    def process(self, client, initiative=False, scenario=None):
        print(f"🔄 {self.name} 开始处理 (initiative={initiative})")
        current_length = len(self.short_memory)
        if current_length == self.last_history_length and not initiative:
            # 没有新事件，无反应
            print(f"⏭️ {self.name} 没有新消息，跳过")
            return {}

        print(f"📝 {self.name} 有 {current_length} 条消息需要处理")

        # 检查并总结如果需要

        system_prompt = self.system_prompt(scenario)

        # Get history from memory
        ctx = self.short_memory.searilize(dialect="default")
        ctx.insert(0, {"role": "system", "content": system_prompt})
        print(f"📤 {self.name} 准备发送 {len(ctx)} 条消息到LLM")

        action_data = None
        for attempt in range(self.max_repeat):
            try:
                llm_output = self.call_llm(client, ctx)
                thoughts, plan, action_block = self._parse_full_response(llm_output)
                actions = self._parse_actions(action_block)
                
                action_data = []
                for action in actions:
                    # Try to parse content as JSON, otherwise treat as raw string
                    try:
                        content_json = json.loads(action["content"])
                        action_data.append({**{"action": action["action"]}, **content_json})
                    except json.JSONDecodeError:
                        action_data.append({"action": action["action"], "message": action["content"]})

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
            "position": self.position,
            "hunger": self.hunger,
            "energy": self.energy,
            "inventory": self.inventory,
            "joined_groups": list(self.joined_groups),
            "map_position": self.map_position,
        }

    @classmethod
    def from_dict(cls, data, action_space_map):
        agent = cls(
            name=data["name"],
            user_profile=data["user_profile"],
            style=data["style"],
            initial_instruction=data["initial_instruction"],
            role_prompt=data["role_prompt"],
            action_space=[action_space_map[action_name] for action_name in data["action_space"]],
            max_repeat=data["max_repeat"],
            position=data["position"],
            hunger=data["hunger"],
            energy=data["energy"],
            inventory=data["inventory"],
            map_position=data["map_position"],
        )
        agent.short_memory.history = data["short_memory"]
        agent.last_history_length = data["last_history_length"]
        agent.joined_groups = set(data["joined_groups"])
        return agent
