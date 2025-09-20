import json
import re
import xml.etree.ElementTree as ET

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

        # Lightweight, scene-agnostic plan state persisted across turns
        self.plan_state = {
            "goals": [],
            "milestones": [],
            "current_focus": {},
            "strategy": "",
            "notes": "",
        }

    def system_prompt(self, scene=None):
        # Render plan state for inclusion in system prompt
        def _fmt_list(items):
            if not items:
                return "- (none)"
            return "\n".join(
                [
                    f"- {item}" if isinstance(item, str) else f"- {item}"
                    for item in items
                ]
            )

        def _fmt_goals(goals):
            if not goals:
                return "- (none)"
            lines = []
            for g in goals:
                gid = g.get("id", "?")
                desc = g.get("desc", "")
                pr = g.get("priority", "")
                st = g.get("status", "pending")
                lines.append(f"- [{gid}] {desc} (priority: {pr}, status: {st})")
            return "\n".join(lines)

        def _fmt_milestones(milestones):
            if not milestones:
                return "- (none)"
            lines = []
            for m in milestones:
                mid = m.get("id", "?")
                desc = m.get("desc", "")
                st = m.get("status", "pending")
                lines.append(f"- [{mid}] {desc} (status: {st})")
            return "\n".join(lines)

        plan_state_block = f"""
Current Plan State (read-only; propose updates via Plan Update):
Goals:
{_fmt_goals(self.plan_state.get("goals"))}

Milestones:
{_fmt_milestones(self.plan_state.get("milestones"))}

Current Focus:
{self.plan_state.get("current_focus", {})}

Strategy:
{self.plan_state.get("strategy", "")}

Notes:
{self.plan_state.get("notes", "")}
"""

        # If plan_state is empty, explicitly ask the model to initialize it
        if not self.plan_state or (
            not self.plan_state.get("goals")
            and not self.plan_state.get("milestones")
            and not self.plan_state.get("current_focus")
        ):
            plan_state_block += "\nPlan State is currently empty. In this turn, include a '--- Plan Update ---' section with a JSON object using 'replace' to initialize goals, milestones (based on your Plan steps), current_focus, and a brief strategy. Keep it concise.\n"

        planning_guidelines = """
General Planning Principles:
- Goals are stable; modify only when genuinely necessary.
- Use your own milestones to track observable progress.
- Keep a single Current Focus and align your Action to it.
- Prefer minimal coherent changes; when adapting, preserve unaffected goals and milestones and state what remains unchanged.
- Privacy: Goals, Milestones, Current Focus, Strategy, and Notes as private working notes.

Plan State JSON Schema (reference):
{
  "goals": [
    {"id": "g1", "desc": "...", "priority": "low|normal|high", "status": "pending|current|done"}
  ],
  "milestones": [
    {"id": "m1", "desc": "...", "status": "pending|done"}
  ],
  "current_focus": {"goal_id": "g1", "step": "..."},
  "strategy": "...",
  "notes": "..."
}

Plan Update JSON Format (you emit this ONLY if changing the plan):
- Use exactly one of:
  1) Replace the entire plan_state:
     {"justification":"...", "replace": {PLAN_STATE_OBJECT}}
  2) Patch fields (arrays replace entirely):
     {"justification":"...", "patch": {"goals":[...], "milestones":[...], "current_focus":{...}, "strategy":"...", "notes":"..."}}
- Missing fields mean no change. Unknown keys are ignored. Output valid JSON only (no comments).
"""

        # Build action catalog and usage
        action_catalog = "\n".join(
            [
                f"- {getattr(action, 'NAME', '')}: {getattr(action, 'DESC', '')}".strip()
                for action in self.action_space
            ]
        )
        action_instructions = "".join(
            getattr(action, "INSTRUCTION", "") for action in self.action_space
        )

        base = f"""
You are {self.name}.
You speak in a {self.style} style.

{self.user_profile}

{self.role_prompt}

{plan_state_block}

{planning_guidelines}

{scene.get_scenario_description() if scene else ""}

{scene.get_behavior_guidelines() if scene else ""}

{self.get_output_format()}

Action Space:

Available Actions:
{action_catalog}

Usage:
{action_instructions}


Here are some examples:
{scene.get_examples() if scene else ""}


Initial instruction:
{self.initial_instruction}
"""
        return base

    def get_output_format(self):
        return """
Planning guidelines:
- Goals: stable end-states. Rarely change; name and describe them briefly.
- Milestones: observable sub-results that indicate progress toward goals.
- Current Focus: the single step you are executing now. Align Action with this.
- Strategy: a brief approach for achieving the goals over time.
- Prefer continuity: preserve unaffected goals/milestones; make the smallest coherent change when adapting to new information. State what stays the same.

Turn Flow:
- Output exactly one Thoughts/Plan/Action block per response (single block).
- You may take multiple actions during your turn, one at a time.
- You will not receive acknowledgments between your own actions.
- If the next step is clear, take it; when finished, yield the floor with <Action name="yield" />.

Your entire response MUST follow the format below. Always include Thoughts, Plan, and Action. Include Plan Update only when you decide to modify the plan.

--- Thoughts ---
Your internal monologue. Analyze the current situation, your persona, your long-term goals, and the information you have.
Re-evaluation: Compare the latest events with your current plan. Is your plan still relevant? Should you add, remove, or reorder steps? Should you jump to a different step instead of proceeding sequentially? Prefer continuity; preserve unaffected goals and milestones. Explicitly state whether you are keeping or changing the plan and why.
Strategy for This Turn: Based on your re-evaluation, state your immediate objective for this turn and the short rationale for how you will achieve it.

--- Plan ---
// Update the living plan if needed; mark your immediate focus with [CURRENT]. Keep steps concise and executable.
1. [Step 1]
2. [Step 2] [CURRENT]
3. [Step 3]


--- Action ---
// Output exactly one Action XML element. No extra text.
// You may take multiple actions in your turn, one at a time. When you are ready to yield the floor, output <Action name="yield" />.
// Example:
// <Action name="send_message"><message>Hi everyone!</message></Action>

--- Plan Update ---
// Optional. Include ONLY if you are changing the plan.
// Output either:
// - no change
// - or a JSON object with either a full `replace` or a partial `patch`, plus an optional natural-language `justification`.
// Example (patch):
// {"justification":"...","patch":{"current_focus":{"goal_id":"g1","step":"..."},"notes":"..."}}
// Example (replace):
// {"justification":"...","replace":{"goals":[...],"milestones":[...],"current_focus":{...},"strategy":"...","notes":"..."}}
// Plan State schema reference:
// {"goals":[{"id":"g1","desc":"...","priority":"low|normal|high","status":"pending|current|done"}],
//  "milestones":[{"id":"m1","desc":"...","status":"pending|done"}],
//  "current_focus":{"goal_id":"g1","step":"..."},
//  "strategy":"...",
//  "notes":"..."}
// JSON must be valid (no comments or trailing commas). If Plan State is empty, initialize it using a `replace`.
"""

    def call_llm(self, clients, messages, client_name="chat"):
        client = clients.get(client_name)
        if not client:
            raise ValueError(f"LLM client '{client_name}' not found.")

        try:
            result = client.chat(messages)
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
        """Extracts thoughts, plan, action block, and optional plan update from the response."""
        thoughts_match = re.search(
            r"--- Thoughts ---\s*(.*?)\s*--- Plan ---", full_response, re.DOTALL
        )
        plan_match = re.search(
            r"--- Plan ---\s*(.*?)\s*--- Action ---", full_response, re.DOTALL
        )
        action_match = re.search(
            r"--- Action ---\s*(.*?)(?:\n--- Plan Update ---|\Z)",
            full_response,
            re.DOTALL,
        )
        plan_update_match = re.search(
            r"--- Plan Update ---\s*(.*)$", full_response, re.DOTALL
        )

        thoughts = thoughts_match.group(1).strip() if thoughts_match else ""
        plan = plan_match.group(1).strip() if plan_match else ""
        action = action_match.group(1).strip() if action_match else ""
        plan_update_block = (
            plan_update_match.group(1).strip() if plan_update_match else ""
        )

        return thoughts, plan, action, plan_update_block

    def _parse_plan_update(self, block):
        """Parse Plan Update block; returns dict with 'replace' or 'patch', and optional 'justification'.
        Accepts 'no change' (case-insensitive) or JSON optionally wrapped in fences.
        """
        if not block:
            return None
        text = block.strip()
        if text.lower().startswith("no change"):
            return None
        # Strip common code fences
        if text.startswith("```"):
            # remove first fence line and trailing fence
            text = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", text)
            text = re.sub(r"\n```\s*$", "", text)
        # Try to locate JSON
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
            if not isinstance(data, dict):
                return None
            # only accept if 'patch' or 'replace' present
            if "replace" in data or "patch" in data:
                return data
            return None
        except json.JSONDecodeError:
            return None

    def _apply_plan_update(self, update):
        """Apply plan update: either full replace or shallow patch with list replacement."""
        if not update:
            return False
        justification = update.get("justification", "")
        if "replace" in update and isinstance(update["replace"], dict):
            self.plan_state = update["replace"]
            if self.log_event:
                self.log_event(
                    "plan_update_applied",
                    {
                        "agent": self.name,
                        "kind": "replace",
                        "justification": justification,
                    },
                )
            return True
        if "patch" in update and isinstance(update["patch"], dict):
            patch = update["patch"]
            for k, v in patch.items():
                # lists replace entirely; dicts shallow-merge; scalars replace
                if isinstance(v, list):
                    self.plan_state[k] = v
                elif isinstance(v, dict):
                    base = self.plan_state.get(k, {})
                    if isinstance(base, dict):
                        merged = base.copy()
                        merged.update(v)
                        self.plan_state[k] = merged
                    else:
                        self.plan_state[k] = v
                else:
                    self.plan_state[k] = v
            if self.log_event:
                self.log_event(
                    "plan_update_applied",
                    {
                        "agent": self.name,
                        "kind": "patch",
                        "justification": justification,
                    },
                )
            return True
        return False

    def _infer_initial_plan_from_plan_text(self, plan_text: str):
        """Infer a minimal initial plan_state from the textual Plan when no Plan Update
        was provided and the plan_state is empty."""
        lines = [l.strip() for l in plan_text.splitlines() if l.strip()]
        steps = []
        current_idx = None
        for l in lines:
            m = re.match(r"\d+\.\s*(.*)", l)
            if m:
                text = m.group(1)
                if "[CURRENT]" in text:
                    text = text.replace("[CURRENT]", "").strip()
                    if current_idx is None:
                        current_idx = len(steps)
                steps.append(text)
        if not steps:
            return False
        milestones = [
            {"id": f"m{i + 1}", "desc": s, "status": "pending"}
            for i, s in enumerate(steps)
        ]
        focus_step = steps[current_idx] if current_idx is not None else steps[0]
        self.plan_state = {
            "goals": [
                {
                    "id": "g1",
                    "desc": "Execute the current multi-step plan",
                    "priority": "normal",
                    "status": "current",
                }
            ],
            "milestones": milestones,
            "current_focus": {"goal_id": "g1", "step": focus_step},
            "strategy": "",
            "notes": "",
        }
        if self.log_event:
            self.log_event(
                "plan_update_inferred",
                {
                    "agent": self.name,
                    "source": "plan_text",
                    "milestones": len(milestones),
                },
            )
        return True

    def _parse_actions(self, action_block):
        """Parses the Action XML block and returns a single action dict.
        Expected format:
          <Action name="send_message"><message>Hi</message></Action>
          <Action name="yield" />
        Returns [dict] with keys: 'action' and child tags as top-level fields.
        """
        if not action_block:
            return []
        text = action_block.strip()
        # Strip code fences
        if text.startswith("```xml") and text.endswith("```"):
            text = text[6:-3].strip()
        elif text.startswith("```") and text.endswith("```"):
            text = text[3:-3].strip()
        elif text.startswith("`") and text.endswith("`"):
            text = text.strip("`")

        # Try parsing whole block as XML first
        xml_str = text
        root = None
        try:
            root = ET.fromstring(xml_str)
        except Exception:
            # Try to locate the first <Action ...>...</Action> or self-closing variant
            m = re.search(r"<Action\b[\s\S]*?</Action>|<Action\b[^>]*/>", text, re.IGNORECASE)
            if not m:
                return []
            frag = m.group(0)
            try:
                root = ET.fromstring(frag)
            except Exception:
                return []

        if root is None or root.tag.lower() != "action":
            return []
        name = root.attrib.get("name") or root.attrib.get("NAME")
        if not name:
            return []
        result = {"action": name}
        # Copy child elements as top-level params (simple text nodes)
        for child in list(root):
            tag = child.tag
            val = (child.text or "").strip()
            if tag and val is not None:
                result[tag] = val
        return [result]

    def process(self, clients, initiative=False, scene=None):
        current_length = len(self.short_memory)
        if current_length == self.last_history_length and not initiative:
            # 没有新事件，无反应
            print(f"No new messages for {self.name}, skipping")
            return {}

        # 检查并总结如果需要

        system_prompt = self.system_prompt(scene)

        # Get history from memory
        ctx = self.short_memory.searilize(dialect="default")
        ctx.insert(0, {"role": "system", "content": system_prompt})

        # Ephemeral action-only nudge for intra-turn calls or when last was assistant
        try:
            last_role = None
            if len(ctx) > 1:
                last_role = ctx[-1].get("role")
            if initiative or last_role == "assistant":
                ctx.append({"role": "user", "parts": ["Continue."]})
        except Exception:
            pass

        action_data = None
        for attempt in range(self.max_repeat):
            try:
                llm_output = self.call_llm(clients, ctx)
                print(
                    f"LLM output for {self.name} (attempt {attempt + 1}):\n{llm_output}\n"
                )
                thoughts, plan, action_block, plan_update_block = (
                    self._parse_full_response(llm_output)
                )
                action_data = self._parse_actions(action_block)
                # Try applying plan update if present
                plan_update = self._parse_plan_update(plan_update_block)
                if plan_update:
                    self._apply_plan_update(plan_update)
                elif (
                    not self.plan_state
                    or (
                        not self.plan_state.get("goals")
                        and not self.plan_state.get("milestones")
                        and not self.plan_state.get("current_focus")
                    )
                ) and plan:
                    # Initialize from textual Plan as a fallback
                    self._infer_initial_plan_from_plan_text(plan)

                if not action_data:
                    raise ValueError("No valid action found in LLM output")

                # If parsing succeeds, break
                break
            except (json.JSONDecodeError, ValueError, openai.APIError) as e:
                print(f"Attempt {attempt + 1} failed for {self.name}: {e}")
                if attempt == self.max_repeat - 1:
                    # On final failure, if intra-turn, yield the floor to avoid stalls
                    if initiative:
                        llm_output = '<Action name="yield" />'
                        action_data = [{"action": "yield"}]
                    else:
                        llm_output = "<Action name=\"yield\" />"  # safe default
                        action_data = [{"action": "yield"}]

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
            "plan_state": self.plan_state,
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
        agent.plan_state = data.get(
            "plan_state",
            {
                "goals": [],
                "milestones": [],
                "current_focus": {},
                "strategy": "",
                "notes": "",
            },
        )
        return agent
