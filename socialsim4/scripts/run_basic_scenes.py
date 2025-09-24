import json
import os
import queue
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List
from urllib.parse import parse_qs, urlparse

from socialsim4.api.schemas import LLMConfig
from socialsim4.core.agent import Agent
from socialsim4.core.event import PublicEvent, StatusEvent
from socialsim4.core.llm import create_llm_client
from socialsim4.core.ordering import (
    ControlledOrdering,
    CycledOrdering,
    LLMModeratedOrdering,
    RandomOrdering,
    SequentialOrdering,
)
from socialsim4.core.scenes.council_scene import CouncilScene
from socialsim4.core.scenes.landlord_scene import LandlordPokerScene
from socialsim4.core.scenes.simple_chat_scene import SimpleChatScene
from socialsim4.core.scenes.village_scene import GameMap, VillageScene
from socialsim4.core.scenes.werewolf_scene import WerewolfScene
from socialsim4.core.simulator import Simulator


def console_logger(event_type: str, data):
    """Compact console logger that prints key simulation events."""
    if event_type == "system_broadcast":
        if data.get("sender") is None or data.get("sender") == "":
            print(f"[Public Event] {data.get('text')}")
    elif event_type == "action_end":
        action_data = data.get("action")
        if action_data.get("action") != "yield":
            print(f"[{action_data.get('action')}] {data.get('summary')}")
    elif event_type == "landlord_deal":
        players = data.get("players", {})
        bottom = data.get("bottom", [])
        print("[Deal] Bottom:", " ".join(bottom))
        for name, toks in players.items():
            print(f"[Deal] {name}:", " ".join(toks))
    # landlord_play event removed from actions; summaries now include details


def make_agents(names: List[str], action_space: List[str]) -> List[Agent]:
    agents = []
    for name in names:
        agents.append(
            Agent.from_dict(
                {
                    "name": name,
                    "user_profile": f"You are {name}.",
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


def build_landlord_sim(num_decks: int = 1) -> Simulator:
    # Four configured players with distinct styles/prompts
    agents = [
        Agent.from_dict(
            {
                "name": "Alice",
                "user_profile": (
                    "You are Alice, an aggressive Dou Dizhu player. You are comfortable calling and robbing with high cards, jokers, or multiple pairs/triples. "
                    "You aim to seize initiative early and pressure opponents with bombs or sequences when possible."
                ),
                "style": "decisive and succinct",
                "initial_instruction": "",
                "role_prompt": (
                    "As a human player, evaluate your hand honestly. Call/rob only when your hand is strong; otherwise pass. "
                    "During play, prefer efficient leads (sequences, triples) and conserve bombs unless needed."
                ),
                "action_space": ["yield"],
                "properties": {},
            }
        ),
        Agent.from_dict(
            {
                "name": "Bob",
                "user_profile": (
                    "You are Bob, a cautious Dou Dizhu player. You call only with very strong hands (e.g., a rocket, multiple bombs, or dominant high cards) and rarely rob. "
                    "You prioritize safe, team-oriented play and avoid risky contests."
                ),
                "style": "calm and methodical",
                "initial_instruction": "",
                "role_prompt": (
                    "Conserve strength for decisive moments. If you cannot beat cleanly, pass. "
                    "When landlord, lead from strength; when farmer, cooperate implicitly by not feeding the landlord."
                ),
                "action_space": ["yield"],
                "properties": {},
            }
        ),
        Agent.from_dict(
            {
                "name": "Carol",
                "user_profile": (
                    "You are Carol, a sequence-focused Dou Dizhu player. You value straights and double sequences, and you manage attachments carefully for airplanes."
                ),
                "style": "analytical and concise",
                "initial_instruction": "",
                "role_prompt": (
                    "If your hand forms strong chains (straights/double seq), favor leading those. "
                    "Protect your combo potential; avoid breaking triples unless necessary."
                ),
                "action_space": ["yield"],
                "properties": {},
            }
        ),
        Agent.from_dict(
            {
                "name": "Dave",
                "user_profile": (
                    "You are Dave, a power player. You give priority to rockets, 2s, and bombs. You will rob when holding rocket or multiple 2s/bombs."
                ),
                "style": "direct and assertive",
                "initial_instruction": "",
                "role_prompt": (
                    "Leverage bombs and rocket to break control. As landlord, push tempo; as farmer, hold power to stop landlord runs."
                ),
                "action_space": ["yield"],
                "properties": {},
            }
        ),
    ]
    scene = LandlordPokerScene(
        "landlord",
        "New game: Dou Dizhu (4 players). Call/rob bidding, doubling stage, full combos.",
        num_decks=num_decks,
    )
    clients = make_clients()

    # Controlled ordering: always schedule the one who should act now
    def next_active(sim):
        s = sim.scene
        p = s.state.get("phase")
        if p == "bidding":
            if s.state.get("bidding_stage") == "call":
                i = s.state.get("bid_turn_index")
                return s.state.get("players")[i]
            else:  # rob stage: find next eligible who hasn't acted
                elig = list(s.state.get("rob_eligible"))
                acted = dict(s.state.get("rob_acted"))
                if not elig:
                    return None
                # start from bid_turn_index and scan cyclically
                names = list(s.state.get("players"))
                start = s.state.get("bid_turn_index")
                n = len(names)
                for off in range(n):
                    idx = (start + off) % n
                    nm = names[idx]
                    if nm in elig and not acted.get(nm, False):
                        return nm
                return None
        if p == "doubling":
            order = list(s.state.get("doubling_order"))
            acted = dict(s.state.get("doubling_acted"))
            if not order:
                return None
            for nm in order:
                if not acted.get(nm, False):
                    return nm
            return None
        if p == "playing":
            i = s.state.get("current_turn")
            return s.state.get("players")[i]
        return None

    sim = Simulator(
        agents,
        scene,
        clients,
        event_handler=console_logger,
        ordering=ControlledOrdering(next_fn=next_active),
        max_steps_per_turn=3,
    )
    sim.broadcast(PublicEvent("Players: " + ", ".join([a.name for a in agents])))
    return sim


def run_landlord_scene():
    print("=== LandlordPokerScene (Dou Dizhu) ===")
    decks = int(os.getenv("LDDZ_DECKS", "2"))
    sim = build_landlord_sim(num_decks=decks)
    sim.run(max_turns=200)


def build_simple_chat_sim() -> Simulator:
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

    clients = make_clients()
    sim = Simulator(
        agents,
        scene,
        clients,
        ordering=SequentialOrdering(),
        event_handler=console_logger,
    )
    sim.broadcast(PublicEvent("Participants: " + ", ".join([a.name for a in agents])))
    sim.broadcast(
        PublicEvent(
            "News: A new study suggests AI models now match human-level performance in several creative writing benchmarks."
        )
    )
    return sim


def run_simple_chat():
    print("=== SimpleChatScene ===")
    sim = build_simple_chat_sim()
    sim.run(max_turns=50)


def build_council_sim() -> Simulator:
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

    clients = make_clients()

    sim = Simulator(
        reps,
        scene,
        clients,
        event_handler=console_logger,
        ordering=SequentialOrdering(),
    )
    # Participants announcement at start
    sim.broadcast(PublicEvent("Participants: " + ", ".join([a.name for a in reps])))
    return sim


def run_council():
    print("=== CouncilScene ===")
    sim = build_council_sim()
    sim.run(max_turns=120)


def build_village_sim() -> Simulator:
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
    return sim


def run_village():
    print("=== VillageScene ===")
    sim = build_village_sim()
    sim.run(max_turns=40)


def build_werewolf_sim() -> Simulator:
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
        "Elena": "werewolf",
        "Bram": "witch",
        "Ronan": "seer",
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
                "- Phase control: start with open discussion; each player may should send at most one message in discussion. \n"
                "- When all have spoken or passed, begin the voting phase by open_voting action; when everyone had a fair chance to vote or revote, close the voting and finish the day.\n"
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
        ordering=CycledOrdering(
            wolves + wolves + seers + witches + names + names + ["Moderator"]
        ),
    )
    return sim


def run_werewolf():
    print("=== WerewolfScene ===")
    sim = build_werewolf_sim()
    sim.run(max_turns=400)


if __name__ == "__main__":
    run_simple_chat()
    # run_council()
    # run_village()

    # run_werewolf()
    # run_landlord_scene()
