import json
import sys
import os
from pathlib import Path
from typing import Dict, List

from socialsim4.api.schemas import LLMConfig
from socialsim4.core.agent import Agent
from socialsim4.core.event import PublicEvent, StatusEvent
from socialsim4.core.llm import create_llm_client
from socialsim4.core.ordering import (
    CycledOrdering,
    LLMModeratedOrdering,
    RandomOrdering,
    SequentialOrdering,
)
from socialsim4.core.scenes.council_scene import CouncilScene
from socialsim4.core.scenes.simple_chat_scene import SimpleChatScene
from socialsim4.core.scenes.village_scene import GameMap, VillageScene
from socialsim4.core.scenes.werewolf_scene import WerewolfScene
from socialsim4.core.simulator import Simulator
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import queue


def console_logger(event_type: str, data):
    """Compact console logger that prints key simulation events."""
    if event_type == "system_broadcast":
        if data.get("sender") is None or data.get("sender") == "":
            print(f"[Public Event] {data.get('text')}")
    elif event_type == "action_end":
        action_data = data.get("action")
        if action_data.get("action") != "yield":
            print(f"[{action_data.get('action')}] {data.get('summary')}")


def make_agents(names: List[str], action_space: List[str]) -> List[Agent]:
    agents = []
    for name in names:
        agents.append(
            Agent.from_dict(
                {
                    "name": name,
                    "user_profile": f"You are {name}, a participant in the simulation.",
                    "style": "concise and natural",
                    "initial_instruction": "",
                    "role_prompt": "",
                    "action_space": action_space,
                    "properties": {},
                }
            )
        )
    return agents


def make_clients() -> Dict[str, object]:
    # Select LLM provider via environment:
    # - LLM_DIALECT=openai with OPENAI_API_KEY, OPENAI_MODEL, optional OPENAI_BASE_URL
    # - LLM_DIALECT=gemini with GEMINI_API_KEY, GEMINI_MODEL
    # - default: mock (no network)
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
            # frequency_penalty=float(os.getenv("GEMINI_FREQUENCY_PENALTY", "0.2")),
            # presence_penalty=float(os.getenv("GEMINI_PRESENCE_PENALTY", "0.2")),
            stream=False,
        )
    else:
        provider = LLMConfig(name="chat", kind="mock", model="mock", dialect="mock")

    return {provider.name: create_llm_client(provider)}


def run_simple_chat():
    print("=== SimpleChatScene ===")
    # agents = make_agents(["Host", "Alice", "Bob"], ["send_message", "yield"])
    agents = [
        Agent.from_dict(
            {
                "name": "Host",
                "user_profile": "You are the host of a chat room. Your role is to facilitate conversation, introduce topics, and ensure everyone has a chance to speak. You are neutral and objective.",
                "style": "welcoming and clear",
                "action_space": ["web_search", "view_page"],
                "initial_instruction": "",
                "role_prompt": "",
                "properties": {},
            }
        ),
        Agent.from_dict(
            {
                "name": "Alice",
                "user_profile": "You are Alice. You are an optimist, full of energy, and always curious about new technologies and their potential to change the world for the better.",
                "style": "enthusiastic and inquisitive",
                "action_space": ["web_search", "view_page"],
                "initial_instruction": "",
                "role_prompt": "",
                "properties": {},
            }
        ),
        Agent.from_dict(
            {
                "name": "Bob",
                "user_profile": "You are Bob. You are a pragmatist and a bit of a skeptic. You are cautious about new technologies and tend to focus on the potential downsides and practical challenges.",
                "style": "cynical and questioning",
                "action_space": ["web_search", "view_page"],
                "initial_instruction": "",
                "role_prompt": "",
                "properties": {},
            }
        ),
    ]

    scene = SimpleChatScene("room", "Welcome to the chat room.")
    # Force mock client for offline, fast dev UI
    from socialsim4.api.schemas import LLMConfig as _LLMC
    from socialsim4.core.llm import create_llm_client as _mk
    _provider = _LLMC(name="chat", kind="mock", model="mock", dialect="mock")
    clients = {_provider.name: _mk(_provider)}

    sim = Simulator(
        agents,
        scene,
        clients,
        ordering=RandomOrdering(),
        event_handler=console_logger,
    )

    # Participants announcement before other messages
    sim.broadcast(PublicEvent("Participants: " + ", ".join([a.name for a in agents])))

    # Broadcast a public announcement before starting the simulation
    sim.broadcast(
        PublicEvent(
            "News: A new study suggests AI models now match human-level performance in several creative writing benchmarks."
        )
    )

    sim.run(max_turns=30)


def run_council():
    print("=== CouncilScene ===")
    # Six participants: a Host + five representatives with realistic profiles
    reps: List[Agent] = [
        Agent.from_dict(
            {
                "name": "Host",
                "user_profile": (
                    "You chair the legislative council. You are neutral, enforce procedure, "
                    "keep time, summarize points fairly, and move the chamber to a vote "
                    "when deliberation has matured. After voting is completed, announce the results clearly."
                ),
                "style": "formal and neutral",
                "initial_instruction": (
                    "Open the session by summarizing the draft, invite concise opening remarks, "
                    "and proceed to a vote when discussion is adequate or after 8 rounds."
                ),
                "role_prompt": "",
                "action_space": [
                    "start_voting",
                    "finish_meeting",
                    "request_brief",
                ],
                "properties": {},
            }
        ),
        Agent.from_dict(
            {
                "name": "Rep. Chen Wei",
                "user_profile": (
                    "Centrist economist representing downtown professionals. Values fiscal responsibility, "
                    "evidence-based policy, and efficient public transit. Open to pilots with clear metrics."
                ),
                "style": "measured and data-driven",
                "initial_instruction": "",
                "role_prompt": "You support pragmatic compromises that balance budgets and benefits.",
                "action_space": [
                    "vote",
                ],
                "properties": {},
            }
        ),
        Agent.from_dict(
            {
                "name": "Rep. Li Na",
                "user_profile": (
                    "Progressive representative focused on air quality, transit affordability, and climate action. "
                    "Advocates equity safeguards for low-income commuters."
                ),
                "style": "principled and empathetic",
                "initial_instruction": "",
                "role_prompt": "Press for strong environmental standards and equity measures.",
                "action_space": [
                    "vote",
                ],
                "properties": {},
            }
        ),
        Agent.from_dict(
            {
                "name": "Rep. Zhang Rui",
                "user_profile": (
                    "Conservative representative prioritizing small businesses, drivers, and administrative simplicity. "
                    "Skeptical of new fees and complex enforcement."
                ),
                "style": "direct and skeptical",
                "initial_instruction": "",
                "role_prompt": "Highlight risks to small business and unintended consequences.",
                "action_space": [
                    "vote",
                ],
                "properties": {},
            }
        ),
        Agent.from_dict(
            {
                "name": "Rep. Wang Mei",
                "user_profile": (
                    "Business-aligned representative for commercial districts. Focused on competitiveness, delivery logistics, "
                    "and predictable operating costs for merchants."
                ),
                "style": "pragmatic and concise",
                "initial_instruction": "",
                "role_prompt": "Seek exemptions/discounts to protect small merchants and logistics.",
                "action_space": [
                    "vote",
                ],
                "properties": {},
            }
        ),
        Agent.from_dict(
            {
                "name": "Rep. Qiao Jun",
                "user_profile": (
                    "Environmentalist representative with a mandate for ambitious climate policy and rapid emissions reduction. "
                    "Supports bold measures if backed by transparent monitoring."
                ),
                "style": "assertive and analytical",
                "initial_instruction": "",
                "role_prompt": "Push for strong air-quality targets and transparent reporting.",
                "action_space": ["send_message", "yield", "vote"],
                "properties": {},
            }
        ),
    ]

    draft_text = (
        "Draft Ordinance: Urban Air Quality and Congestion Management (Pilot).\n"
        "1) Establish a 12-month congestion charge pilot in the Central Business District (CBD).\n"
        "   - Hours: Weekdays 07:00–19:00; dynamic pricing with a base fee of 30 CNY per entry.\n"
        "   - Exemptions: public buses, emergency vehicles, disability permit holders.\n"
        "   - Resident relief: 50% discount for registered residents within the zone (cap of 20 entries/month).\n"
        "2) Revenue ring-fenced for public transit upgrades, bike lanes, and air-quality programs (audited quarterly).\n"
        "3) Monitoring & transparency: monthly public dashboard on PM2.5/NOx levels, average traffic speed, transit ridership.\n"
        "4) Enforcement: camera-based plate recognition with strict privacy and data-retention limits.\n"
        "5) Independent evaluation at 12 months with specific success criteria (≥15% traffic reduction, ≥10% PM2.5 reduction).\n"
        "   Council decides to terminate, modify, or expand based on evidence."
    )

    scene = CouncilScene(
        "council",
        f"The chamber will now consider the following draft for debate and vote:\n{draft_text}",
    )

    # Use mock client for fast, offline dev UI
    from socialsim4.api.schemas import LLMConfig as _LLMC
    from socialsim4.core.llm import create_llm_client as _mk
    _provider = _LLMC(name="chat", kind="mock", model="mock", dialect="mock")
    clients = {_provider.name: _mk(_provider)}

    sim = Simulator(
        reps,
        scene,
        clients,
        event_handler=console_logger,
        ordering=SequentialOrdering(),
    )
    # Participants announcement at start
    sim.broadcast(PublicEvent("Participants: " + ", ".join([a.name for a in reps])))
    sim.run(max_turns=120)


def run_village():
    print("=== VillageScene ===")
    agents = [
        Agent.from_dict(
            {
                "name": "Elias Thorne",
                "user_profile": "You are Elias Thorne, a reclusive scholar living in a remote village. You are deeply knowledgeable about local history, folklore, and ancient ruins. You spend most of your time in your library, poring over old maps and texts. You are logical, reserved, and slightly suspicious of outsiders.",
                "style": "academic and precise",
                "initial_instruction": "Villagers reported a faint humming near the ancient_ruins after dusk. Investigate the ruins for inscriptions or signs and share your findings.",
                "role_prompt": "Focus on observation and careful inference; verify clues at nearby landmarks.",
                "action_space": [
                    "talk_to",
                    "yield",
                    "move_to_location",
                    "look_around",
                    "gather_resource",
                    "rest",
                ],
                "properties": {"map_xy": [3, 3]},
            }
        ),
        Agent.from_dict(
            {
                "name": "Seraphina",
                "user_profile": "You are Seraphina, the village herbalist. You have an intimate connection with the natural world and possess a deep understanding of plants and their properties. You are compassionate, intuitive, and respected by the villagers for your healing skills. You live in a small cottage near the forest.",
                "style": "gentle and mystical",
                "initial_instruction": "Plants at the forest edge seem to wilt. Forage a few samples and brew a simple diagnostic infusion to assess the cause.",
                "role_prompt": "Act with care; gather sustainable amounts and observe the environment.",
                "action_space": [
                    "talk_to",
                    "yield",
                    "move_to_location",
                    "look_around",
                    "gather_resource",
                    "rest",
                ],
                "properties": {"map_xy": [18, 12]},
            }
        ),
        Agent.from_dict(
            {
                "name": "Kaelen",
                "user_profile": "You are Kaelen, the village blacksmith. You are a person of few words but immense skill. Your forge is the heart of the village, where you craft tools, weapons, and intricate metalwork. You are stoic, practical, and fiercely protective of your community.",
                "style": "terse and direct",
                "initial_instruction": "The public well at the village_center is weak. Gather iron from the mine to forge a sturdier pump coupling.",
                "role_prompt": "Prioritize practical tasks that help the village; keep messages brief.",
                "action_space": [
                    "talk_to",
                    "yield",
                    "move_to_location",
                    "look_around",
                    "gather_resource",
                    "rest",
                ],
                "properties": {"map_xy": [10, 8]},
            }
        ),
        Agent.from_dict(
            {
                "name": "Lyra",
                "user_profile": "You are Lyra, a young and adventurous cartographer. You are new to the village, drawn by tales of its mysterious surroundings. You are curious, energetic, and eager to map the uncharted territories around the village.",
                "style": "enthusiastic and inquisitive",
                "initial_instruction": "Update your map with nearby landmarks. Verify forest paths and locate the waterfall near the forest edge.",
                "role_prompt": "Explore efficiently and share helpful wayfinding notes.",
                "action_space": [
                    "talk_to",
                    "yield",
                    "move_to_location",
                    "look_around",
                    "gather_resource",
                    "rest",
                ],
                "properties": {"map_xy": [15, 15]},
            }
        ),
    ]

    with open(Path(__file__).parent / "default_map.json") as f:
        map_data = json.load(f)
    game_map = GameMap.from_dict(map_data)

    scene = VillageScene(
        "village",
        "The sun rises over the quiet village of Silverwood, nestled in a valley surrounded by ancient forests and mist-shrouded hills. A new day brings with it new mysteries and challenges.",
        game_map=game_map,
        # print_map_each_turn=True,
    )
    clients = make_clients()

    sim = Simulator(
        agents,
        scene,
        clients,
        event_handler=console_logger,
        ordering=SequentialOrdering(),
    )

    # Participants announcement at start
    sim.broadcast(PublicEvent("Participants: " + ", ".join([a.name for a in agents])))

    sim.broadcast(
        PublicEvent(
            "At sunrise, word spreads in the village_center: the well's flow is weak, and a faint humming has been heard near the ancient_ruins after dusk."
        )
    )

    sim.run(max_turns=40)


def run_werewolf():
    print("=== WerewolfScene ===")
    # Define a fixed cast and roles for determinism in the demo
    names = [
        "Moderator",
        "Elena",
        "Bram",
        "Ronan",
        "Mira",
        "Pia",
        "Taro",
        "Ava",  # new villager
        "Niko",  # new werewolf
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
                "- You should remind the wolves to vote after their discussion.\n"
                # "- Scheduling: you need to schedule the order for the next few rounds if system explicitly requests it.\n"
                "- Phase control: start with open discussion; each player may should send at most one message in discussion. When all have spoken or passed, begin the voting phase by open_voting action; when everyone had a fair chance to vote or revote, close the voting and finish the day.\n"
                "- Clarity: make brief, procedural reminders (e.g., 'Final statements', 'Voting soon', 'Please cast or update your vote'). Keep announcements short.\n"
                "- Discipline: never reveal or summarize hidden information; do not speculate or pressure specific outcomes.\n"
                # '- Scheduling: when asked by the system to schedule, emit exactly one action and nothing else: <Action name="schedule_order"><order>["Name1", "Name2"]</order></Action>.\n'
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
        # Assign only role-specific actions here; common actions are provided by the scene.
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
                    "properties": {
                        "role": r,
                    },
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

    sim = Simulator(
        agents,
        scene,
        clients,
        event_handler=console_logger,
        ordering=CycledOrdering(wolves + wolves + seers + witches + names + names),
    )
    # Run with a generous cap; simulation stops early when the scene declares completion.
    sim.run(max_turns=400)


# ----- Dev UI (simple, local; no external deps) -----
class StepRunner:
    def __init__(self, sim: Simulator):
        self.sim = sim
        self.order_iter = self.sim.ordering.iter()
        # Flush any queued broadcasts at start
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


class DevEventBus:
    def __init__(self, max_history=5000):
        self.subscribers: List[queue.Queue] = []
        self.history: List[str] = []
        self.max_history = max_history
        self.lock = threading.Lock()

    def subscribe(self) -> queue.Queue:
        q = queue.Queue()
        with self.lock:
            self.subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        with self.lock:
            self.subscribers = [s for s in self.subscribers if s is not q]

    def publish(self, event_type: str, data: dict):
        payload = json.dumps({"type": event_type, "data": data})
        with self.lock:
            self.history.append(payload)
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history :]
            subs = list(self.subscribers)
        for q in subs:
            q.put(payload)


class SimStepWorker(threading.Thread):
    def __init__(self, runner: StepRunner):
        super().__init__(daemon=True)
        self.runner = runner
        self.cmd_q: queue.Queue = queue.Queue()

    def enqueue_step(self, n: int):
        self.cmd_q.put(("step", n))

    def run(self):
        while True:
            cmd, n = self.cmd_q.get()
            if cmd == "step":
                self.runner.step_n(int(n))


def run_werewolf_dev_webui():
    print("=== WerewolfScene (Dev Web UI) ===")
    # Build the same scenario as run_werewolf, but don't auto-run; serve a web UI
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
    initial_text = (
        f"Welcome to Werewolf. {participants_line}. Roles are assigned privately. \nNight has fallen. Please close your eyes."
    )
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

    bus = DevEventBus()

    def dev_event_handler(event_type: str, data):
        bus.publish(event_type, data)

    sim = Simulator(
        agents,
        scene,
        clients,
        event_handler=dev_event_handler,
        ordering=CycledOrdering(wolves + wolves + seers + witches + names + names),
    )

    runner = StepRunner(sim)
    worker = SimStepWorker(runner)
    worker.start()

    index_html = """
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>SocialSim4 Dev UI</title>
  <style>
    :root { font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; font-size: 16px; }
    body { margin: 0; background: #0b0f19; color: #e6e6e6; }
    .grid { display: grid; grid-template-columns: 2fr 1fr; gap: 12px; height: 100vh; }
    header { padding: 10px 14px; background: #0f1526; border-bottom: 1px solid #1d2744; }
    .pane { padding: 10px; overflow: hidden; }
    .panel { height: calc(100vh - 64px); background: #0f1526; border: 1px solid #1d2744; border-radius: 8px; display: flex; flex-direction: column; }
    .feed { flex: 1; overflow: auto; padding: 10px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, \"Liberation Mono\", monospace; font-size: 14px; line-height: 1.4; }
    .controls { padding: 8px; border-top: 1px solid #1d2744; display: flex; gap: 8px; }
    .btn { background: #223053; color: #e6e6e6; border: 1px solid #2c3b63; border-radius: 6px; padding: 8px 10px; cursor: pointer; }
    .btn:hover { background: #2a3a66; }
    .side { display: flex; flex-direction: column; height: 100%; }
    .list { height: 180px; overflow: auto; border-bottom: 1px solid #1d2744; }
    .agent { padding: 8px 10px; cursor: pointer; border-bottom: 1px solid #172140; }
    .agent:hover { background: #162346; }
    .agent.active { background: #1b2a54; }
    .ctx { flex: 1; overflow: auto; padding: 10px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; background: #0b1020; }
    .pill { display: inline-block; padding: 2px 6px; margin-right: 6px; border-radius: 9999px; font-size: 12px; border: 1px solid #2c3b63; background: #1a2648; color: #d0d8ff; }
    .evt { margin-bottom: 8px; }
    .evt .head { color: #aab7ff; }
  </style>
</head>
<body>
  <header>
    <strong>SocialSim4 – Werewolf (Dev UI)</strong>
    <span id="hdr" style="margin-left:12px; opacity:.8"></span>
  </header>
  <div class=\"grid\">
    <div class=\"pane\">
      <div class=\"panel\">
        <div id=\"feed\" class=\"feed\"></div>
        <div class=\"controls\">
          <button class=\"btn\" onclick=\"step(1)\">Run 1 turn</button>
          <button class=\"btn\" onclick=\"step(10)\">Run 10 turns</button>
          <button class=\"btn\" onclick=\"step(50)\">Run 50 turns</button>
        </div>
      </div>
    </div>
    <div class=\"pane\">
      <div class=\"panel side\">
        <div id=\"agents\" class=\"list\"></div>
        <div id=\"ctx\" class=\"ctx\"></div>
      </div>
    </div>
  </div>
  <script>
    const feed = document.getElementById('feed');
    const agentsEl = document.getElementById('agents');
    const ctxEl = document.getElementById('ctx');
    let currentAgent = null;
    const PRE_AGENTS = __AGENTS__;

    function append(text) {
      const div = document.createElement('div');
      div.className = 'evt';
      div.innerHTML = text;
      feed.appendChild(div);
      feed.scrollTop = feed.scrollHeight;
    }

    function esc(s) { return s.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }

    function renderEvent(msg) {
      const t = msg.type;
      const d = msg.data || {};
      if (t === 'system_broadcast') {
        append(`<span class=\"pill\">Broadcast</span> ${esc(d.text || '')}`);
        return;
      }
      if (t === 'action_start') {
        append(`<span class=\"pill\">Action</span> ${esc(d.agent)} -> ${esc((d.action||{}).action || '')}`);
        return;
      }
      if (t === 'action_end') {
        append(`<span class=\"pill\">Result</span> ${esc(d.agent)}: ${esc(d.summary || '')}`);
        return;
      }
      if (t === 'agent_process_start') {
        append(`<span class=\"pill\">Process</span> ${esc(d.agent)} step ${d.step}`);
        return;
      }
      if (t === 'agent_process_end') {
        append(`<span class=\"pill\">Process End</span> ${esc(d.agent)} step ${d.step}`);
        return;
      }
      append(`<span class=\"pill\">${esc(t)}</span> ${esc(JSON.stringify(d))}`);
    }

    function renderAgents(list) {
        agentsEl.innerHTML = '';
        list.forEach(name => {
          const div = document.createElement('div');
          div.className = 'agent' + (name === currentAgent ? ' active' : '');
          div.textContent = name;
          div.onclick = () => { currentAgent = name; hydrateContext();
            Array.from(agentsEl.children).forEach(c => c.classList.remove('active'));
            div.classList.add('active');
          };
          agentsEl.appendChild(div);
        });
        if (!currentAgent && list.length) { currentAgent = list[0]; hydrateContext(); agentsEl.firstChild.classList.add('active'); }
    }

    function hydrateAgents() {
      if (Array.isArray(PRE_AGENTS) && PRE_AGENTS.length) {
        renderAgents(PRE_AGENTS);
      }
      fetch('/agents').then(r => r.json()).then(list => renderAgents(list)).catch(()=>{});
    }

    function hydrateContext() {
      if (!currentAgent) return;
      fetch('/agent?name=' + encodeURIComponent(currentAgent)).then(r => r.json()).then(a => {
        const lines = [];
        lines.push(`<div><strong>${esc(a.name)}</strong> <span class=\"pill\">${esc(a.role || '')}</span></div>`);
        lines.push('<div style=\"margin:8px 0\"><em>Plan State</em></div>');
        lines.push('<pre>' + esc(JSON.stringify(a.plan_state, null, 2)) + '</pre>');
        lines.push('<div style=\"margin:8px 0\"><em>Recent Context (last 20)</em></div>');
        const tail = (a.short_memory || []).slice(-20);
        lines.push('<pre>' + esc(tail.map(m => `- [${m.role}] ${m.content}`).join('\n')) + '</pre>');
        ctxEl.innerHTML = lines.join('\n');
      })
    }

    function step(n) {
      fetch('/step?n=' + n, { method: 'POST' })
        .then(r => r.json())
        .then(j => append(`<span class=\"pill\">UI</span> enqueued ${j.n} turn(s)`))
        .catch(err => append(`<span class=\"pill\">UI</span> error: ${esc(String(err))}`));
    }

    function tickScene() {
      fetch('/scene').then(r => r.json()).then(s => {
        const p = s.phase || '?';
        const d = Number(s.day) || 0;
        const t = Number(s.turns) || 0;
        document.getElementById('hdr').textContent = `phase: ${p}, day: ${d}, turns: ${t}`;
      }).catch(() => {});
    }

    hydrateAgents();
    const es = new EventSource('/events?history=1');
    es.onmessage = ev => { try { const msg = JSON.parse(ev.data); renderEvent(msg); } catch (_) {} };
    setInterval(tickScene, 1000);
  </script>
</body>
</html>
"""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/":
                names_json = json.dumps(list(sim.agents.keys()))
                body = index_html.replace("__AGENTS__", names_json).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if parsed.path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            if parsed.path == "/agents":
                names_json = json.dumps(list(sim.agents.keys())).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(names_json)))
                self.end_headers()
                self.wfile.write(names_json)
                return
            if parsed.path == "/agent":
                q = parse_qs(parsed.query)
                name = q.get("name", [""])[0]
                a = sim.agents.get(name)
                data = {
                    "name": a.name,
                    "role": a.properties.get("role"),
                    "plan_state": a.plan_state,
                    "short_memory": a.short_memory.get_all(),
                }
                body = json.dumps(data).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if parsed.path == "/events":
                q = parse_qs(parsed.query)
                history = q.get("history", ["0"])[0] == "1"
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                if history:
                    for item in bus.history:
                        self.wfile.write(b"data: " + item.encode("utf-8") + b"\n\n")
                        self.wfile.flush()
                sub = bus.subscribe()
                while True:
                    item = sub.get()
                    self.wfile.write(b"data: " + item.encode("utf-8") + b"\n\n")
                    self.wfile.flush()
            if parsed.path == "/scene":
                data = {
                    "turns": sim.turns,
                    "phase": sim.scene.state.get("phase"),
                    "time": sim.scene.state.get("time"),
                    "day": sim.scene.state.get("day_count"),
                }
                body = json.dumps(data).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

        def do_POST(self):
            parsed = urlparse(self.path)
            if parsed.path == "/step":
                q = parse_qs(parsed.query)
                n = int(q.get("n", ["1"])[0])
                worker.enqueue_step(n)
                resp = json.dumps({"accepted": True, "n": n}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
                return

    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("Dev UI at http://127.0.0.1:8765/")
    server.serve_forever()


if __name__ == "__main__":
    # run_simple_chat()
    # run_council()
    # run_village()
    if "--dev-ui" in sys.argv or "--dev-webui" in sys.argv:
        run_werewolf_dev_webui()
    else:
        run_werewolf()
