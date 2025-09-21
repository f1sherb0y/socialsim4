import json
import os
import sys
from pathlib import Path
from typing import Dict, List

from socialsim4.api.schemas import LLMConfig
from socialsim4.core.agent import Agent
from socialsim4.core.event import PublicEvent
from socialsim4.core.llm import create_llm_client
from socialsim4.core.scenes.council_scene import CouncilScene
from socialsim4.core.scenes.simple_chat_scene import SimpleChatScene
from socialsim4.core.scenes.village_scene import GameMap, VillageScene
from socialsim4.core.scenes.werewolf_scene import WerewolfScene
from socialsim4.core.simulator import Simulator


def console_logger(event_type: str, data):
    """Compact console logger that prints key simulation events.

    - action_start/action_end, agent_process_start/agent_process_end: JSON payload
    - event_recorded: plain transcript of events (Public/Status/Speak)
    - log_recorded: plain transcript of notes (e.g., web_search/view_page)
    - send_message/web_search/view_page/yield: JSON payload
    """
    if event_type in (
        "action_end",
        "send_message",
        "web_search",
        "view_page",
        "yield",
    ):
        print(f"[{event_type}] {json.dumps(data, ensure_ascii=False)}")
    elif event_type in ("event_recorded", "log_recorded"):
        text = data.get("text", "") if isinstance(data, dict) else str(data)
        tag = "event" if event_type == "event_recorded" else "note"
        print(f"[{tag}] {text}")


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
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            dialect="gemini",
            api_key=os.getenv("GEMINI_API_KEY"),
            temperature=float(os.getenv("GEMINI_TEMPERATURE", "1.0")),
            max_tokens=int(os.getenv("GEMINI_MAX_TOKENS", "65536")),
            top_p=float(os.getenv("GEMINI_TOP_P", "1.0")),
            frequency_penalty=float(os.getenv("GEMINI_FREQUENCY_PENALTY", "0.2")),
            presence_penalty=float(os.getenv("GEMINI_PRESENCE_PENALTY", "0.2")),
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
    clients = make_clients()

    sim = Simulator(agents, scene, clients, event_handler=console_logger)

    # Participants announcement before other messages
    sim.broadcast(PublicEvent("Participants: " + ", ".join([a.name for a in agents])))

    # Broadcast a public announcement before starting the simulation
    sim.broadcast(
        PublicEvent(
            "News: A new study suggests AI models now match human-level performance in several creative writing benchmarks."
        )
    )

    sim.run(num_rounds=5)
    print(sim.get_timeline())


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
                "action_space": ["send_message", "yield", "vote", "get_rounds"],
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

    sim = Simulator(reps, scene, clients, event_handler=console_logger)
    # Participants announcement at start
    sim.broadcast(PublicEvent("Participants: " + ", ".join([a.name for a in reps])))
    sim.run(num_rounds=15)
    print(sim.get_timeline())


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
    )
    clients = make_clients()

    sim = Simulator(agents, scene, clients, event_handler=console_logger)

    # Participants announcement at start
    sim.broadcast(PublicEvent("Participants: " + ", ".join([a.name for a in agents])))

    sim.broadcast(
        PublicEvent(
            "At sunrise, word spreads in the village_center: the well's flow is weak, and a faint humming has been heard near the ancient_ruins after dusk."
        )
    )

    sim.run(num_rounds=5)
    print(sim.get_timeline())


def run_werewolf():
    print("=== WerewolfScene ===")
    # Define a fixed cast and roles for determinism in the demo
    names = ["Moderator", "Elena", "Bram", "Ronan", "Mira", "Pia", "Taro"]
    role_map = {
        "Elena": "seer",
        "Bram": "witch",
        "Ronan": "werewolf",
        "Mira": "werewolf",
        "Pia": "villager",
        "Taro": "villager",
    }

    def role_prompt(name):
        if name == "Moderator":
            return (
                "You are the Moderator. Your job is to direct the day flow fairly and clearly.\n"
                "Behavioral guidelines:\n"
                "- Neutrality: do not take sides or hint at hidden roles. Avoid speculation.\n"
                "- Phase control: start with open discussion; each player may should send at most one message in discussion. When all have spoken or passed, begin the voting phase; when everyone had a fair chance to vote or revote, close the voting and finish the day.\n"
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
    initial_text = f"Welcome to Werewolf. {participants_line}. Roles are assigned privately. Night begins."
    scene = WerewolfScene(
        "werewolf_village",
        initial_text,
        role_map=role_map,
        moderator_names=["Moderator"],
    )
    clients = make_clients()

    sim = Simulator(agents, scene, clients, event_handler=console_logger)
    # Run with a generous cap; simulation stops early when the scene declares completion.
    sim.run(num_rounds=50)
    print(sim.get_timeline())


if __name__ == "__main__":
    # run_simple_chat()
    # run_council()
    run_village()
    # run_werewolf()
