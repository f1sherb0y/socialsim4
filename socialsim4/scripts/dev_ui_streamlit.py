import os
from typing import Dict, List

import streamlit as st

from socialsim4.api.schemas import LLMConfig
from socialsim4.core.agent import Agent
from socialsim4.core.event import PublicEvent, StatusEvent
from socialsim4.core.llm import create_llm_client
from socialsim4.core.ordering import CycledOrdering
from socialsim4.core.scenes.werewolf_scene import WerewolfScene
from socialsim4.core.simulator import Simulator


class DevEventBus:
    def __init__(self, max_history: int = 5000):
        self.history: List[dict] = []
        self.max_history = max_history

    def publish(self, event_type: str, data: dict):
        self.history.append({"type": event_type, "data": data})
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history :]


class StepRunner:
    def __init__(self, sim: Simulator):
        self.sim = sim
        self.order_iter = self.sim.ordering.iter()
        self.sim.emit_remaining_events()

    def step_turn(self):
        if self.sim.scene.is_complete():
            return
        agent_name = next(self.order_iter)
        agent = self.sim.agents.get(agent_name)
        if not agent:
            return
        status_prompt = self.sim.scene.get_agent_status_prompt(agent)
        if status_prompt:
            evt = StatusEvent(status_prompt)
            text = evt.to_string(self.sim.scene.state.get("time"))
            agent.add_env_feedback(text)
        if self.sim.scene.should_skip_turn(agent, self.sim):
            self.sim.scene.post_turn(agent, self.sim)
            self.sim.ordering.post_turn(agent.name)
            self.sim.turns += 1
            self.sim.emit_remaining_events()
            return
        steps = 0
        first_step = True
        continue_turn = True
        self.sim.emit_remaining_events()
        while continue_turn and steps < self.sim.max_steps_per_turn:
            self.sim.emit_event(
                "agent_process_start", {"agent": agent.name, "step": steps + 1}
            )
            action_datas = agent.process(
                self.sim.clients,
                initiative=(self.sim.turns == 0 or not first_step),
                scene=self.sim.scene,
            )
            self.sim.emit_event(
                "agent_process_end",
                {
                    "agent": agent.name,
                    "step": steps + 1,
                    "actions": action_datas,
                },
            )
            if not action_datas:
                break
            yielded = False
            for action_data in action_datas:
                if not action_data:
                    continue
                self.sim.emit_event(
                    "action_start", {"agent": agent.name, "action": action_data}
                )
                success, result, summary = self.sim.scene.parse_and_handle_action(
                    action_data, agent, self.sim
                )
                self.sim.emit_event(
                    "action_end",
                    {
                        "agent": agent.name,
                        "action": action_data,
                        "success": success,
                        "result": result,
                        "summary": summary,
                    },
                )
                self.sim.emit_remaining_events()
                if action_data.get("action") == "yield":
                    yielded = True
                    break
            steps += 1
            first_step = False
            if yielded:
                continue_turn = False
        self.sim.scene.post_turn(agent, self.sim)
        self.sim.emit_remaining_events()
        self.sim.ordering.post_turn(agent.name)
        self.sim.turns += 1

    def step_n(self, n: int):
        for _ in range(n):
            if self.sim.scene.is_complete():
                break
            self.step_turn()


def make_clients() -> Dict[str, object]:
    dialect = os.getenv("LLM_DIALECT", "mock").lower()
    if dialect == "openai":
        provider = LLMConfig(
            name="chat",
            kind="openai",
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            dialect="openai",
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "1.0")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "65536")),
            top_p=float(os.getenv("OPENAI_TOP_P", "1.0")),
            frequency_penalty=float(os.getenv("OPENAI_FREQUENCY_PENALTY", "0.2")),
            presence_penalty=float(os.getenv("OPENAI_PRESENCE_PENALTY", "0.2")),
            stream=False,
        )
    elif dialect == "gemini":
        provider = LLMConfig(
            name="chat",
            kind="gemini",
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            dialect="gemini",
            api_key=os.getenv("GEMINI_API_KEY"),
            temperature=float(os.getenv("GEMINI_TEMPERATURE", "1.0")),
            max_tokens=int(os.getenv("GEMINI_MAX_TOKENS", "65536")),
            top_p=float(os.getenv("GEMINI_TOP_P", "1.0")),
            stream=False,
        )
    else:
        provider = LLMConfig(name="chat", kind="mock", model="mock", dialect="mock")
    return {provider.name: create_llm_client(provider)}


def build_werewolf_sim(bus: DevEventBus) -> tuple[Simulator, List[str]]:
    names = [
        "Moderator",
        "Elena",
        "Bram",
        "Ronan",
        "Mira",
        "Pia",
        "Taro",
        "Ava",
        "Niko",
    ]
    role_map = {
        "Elena": "seer",
        "Bram": "witch",
        "Ronan": "werewolf",
        "Mira": "werewolf",
        "Pia": "villager",
        "Taro": "villager",
        "Ava": "villager",
        "Niko": "werewolf",
    }

    def role_prompt(name):
        if name == "Moderator":
            return (
                "You are the Moderator. Your job is to direct the day flow fairly and clearly.\n"
                "Behavioral guidelines:\n"
                "- Neutrality: do not take sides or hint at hidden roles. Avoid speculation.\n"
                "- Phase control: start with open discussion; each player may should send at most one message in discussion. When all have spoken or passed, begin the voting phase by open_voting action; when everyone had a fair chance to vote or revote, close the voting and finish the day.\n"
                "- Clarity: make brief, procedural reminders (e.g., 'Final statements', 'Voting soon', 'Please cast or update your vote'). Keep announcements short.\n"
                "- Discipline: never reveal or summarize hidden information; do not speculate or pressure specific outcomes.\n"
            )
        r = role_map.get(name, "villager")
        if r == "werewolf":
            return "You are a Werewolf. Coordinate discreetly with other wolves and eliminate villagers at night."
        if r == "seer":
            return "You are the Seer. Each night you may inspect one player to learn whether they are a werewolf."
        if r == "witch":
            return "You are the Witch. You have two potions total: one to save the night victim, one to poison a player (each once)."
        return "You are a Villager. You have no night power; use discussion and voting to find werewolves."

    agents: List[Agent] = []
    for name in names:
        r = role_map.get(name)
        if name == "Moderator":
            actions = ["open_voting", "close_voting"]
        elif r == "werewolf":
            actions = ["night_kill"]
        elif r == "seer":
            actions = ["inspect"]
        elif r == "witch":
            actions = ["witch_save", "witch_poison"]
        else:
            actions = []
        agents.append(
            Agent.from_dict(
                {
                    "name": name,
                    "user_profile": role_prompt(name),
                    "style": "concise and natural",
                    "initial_instruction": "",
                    "role_prompt": "",
                    "action_space": actions,
                    "properties": {"role": r},
                }
            )
        )

    participants_line = "Participants: " + ", ".join(names)
    initial_text = f"Welcome to Werewolf. {participants_line}. Roles are assigned privately. \nNight has fallen. Please close your eyes."
    scene = WerewolfScene(
        "werewolf_village",
        initial_text,
        role_map=role_map,
        moderator_names=["Moderator"],
    )

    clients = make_clients()

    wolves = [n for n in names if role_map.get(n) == "werewolf"]
    witches = [n for n in names if role_map.get(n) == "witch"]
    seers = [n for n in names if role_map.get(n) == "seer"]

    def event_handler(event_type: str, data):
        bus.publish(event_type, data)

    sim = Simulator(
        agents,
        scene,
        clients,
        event_handler=event_handler,
        ordering=CycledOrdering(wolves + wolves + seers + witches + names + names),
    )

    # sim.broadcast(PublicEvent("Participants: " + ", ".join([a.name for a in agents])))
    # sim.emit_remaining_events()
    return sim, names


def _init_session():
    if "bus" not in st.session_state:
        st.session_state["bus"] = DevEventBus()
    if "sim" not in st.session_state:
        sim, names = build_werewolf_sim(st.session_state["bus"])
        st.session_state["sim"] = sim
        st.session_state["names"] = names
        st.session_state["runner"] = StepRunner(sim)
        st.session_state["selected_agent"] = names[0]


st.set_page_config(page_title="SocialSim4 Dev UI", layout="wide")
_init_session()

bus: DevEventBus = st.session_state["bus"]
sim: Simulator = st.session_state["sim"]
runner: StepRunner = st.session_state["runner"]
names: List[str] = st.session_state["names"]

left, right = st.columns([2, 1])

with left:
    st.subheader("Events & Actions")
    b1, b10, b50 = st.columns([1, 1, 1])
    if b1.button("Run 1 turn"):
        runner.step_n(1)
    if b10.button("Run 10 turns"):
        runner.step_n(10)
    if b50.button("Run 50 turns"):
        runner.step_n(50)

    # Render last 200 events in the original console_logger format
    feed_lines: List[str] = []
    for item in bus.history[-200:]:
        t = item.get("type")
        d = item.get("data", {})
        if t == "system_broadcast":
            if d.get("sender") is None or d.get("sender") == "":
                feed_lines.append(f"[Public Event] {d.get('text', '')}")
        elif t == "action_end":
            action_data = d.get("action", {})
            if action_data.get("action") != "yield":
                feed_lines.append(f"[{action_data.get('action')}] {d.get('summary')}")
    st.code("\n".join(feed_lines) if feed_lines else "(no events yet)")

with right:
    st.subheader("Agents")
    if "selected_agent" not in st.session_state:
        st.session_state["selected_agent"] = names[0]
    st.radio(
        "Select agent",
        names,
        key="selected_agent",
        label_visibility="collapsed",
    )
    a = sim.agents.get(st.session_state["selected_agent"])
    st.caption(f"Role: {a.properties.get('role')}")
    st.markdown("Plan State")
    st.json(a.plan_state)
    st.markdown("Full Context")
    msgs = a.short_memory.get_all()
    if msgs:
        for m in msgs:
            st.markdown(f"- [{m['role']}]")
            st.code(m["content"])
    else:
        st.caption("(empty)")
