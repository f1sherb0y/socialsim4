import json
import os
import sys
from pathlib import Path
from typing import Dict, List

from socialsimv4.api.schemas import LLMConfig
from socialsimv4.core.agent import Agent
from socialsimv4.core.event import PublicEvent
from socialsimv4.core.llm import create_llm_client
from socialsimv4.core.scenes.council_scene import CouncilScene
from socialsimv4.core.scenes.simple_chat_scene import SimpleChatScene
from socialsimv4.core.scenes.village_scene import GameMap, VillageScene
from socialsimv4.core.simulator import Simulator


def console_logger(event_type: str, data):
    if (
        # event_type == "action_start"
        event_type == "send_message"
        or event_type == "view_page"
        or event_type == "web_search"
        or event_type == "yield"
    ):
        try:
            print(f"[{event_type}] {json.dumps(data, ensure_ascii=False)}")
        except Exception:
            print(f"[{event_type}] {data}")


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
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "65536")),
            top_p=float(os.getenv("OPENAI_TOP_P", "1.0")),
            frequency_penalty=float(os.getenv("OPENAI_FREQUENCY_PENALTY", "0.0")),
            presence_penalty=float(os.getenv("OPENAI_PRESENCE_PENALTY", "0.0")),
            stream=False,
        )
    elif dialect == "gemini":
        provider = LLMConfig(
            name="chat",
            kind="gemini",
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            dialect="gemini",
            api_key=os.getenv("GEMINI_API_KEY"),
            temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("GEMINI_MAX_TOKENS", "65536")),
            top_p=float(os.getenv("GEMINI_TOP_P", "1.0")),
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
                "action_space": ["send_message", "yield"],
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
                "action_space": ["send_message", "yield"],
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
                "action_space": ["send_message", "yield"],
                "initial_instruction": "",
                "role_prompt": "",
                "properties": {},
            }
        ),
    ]

    scene = SimpleChatScene("room", "Welcome to the chat room.")
    clients = make_clients()

    sim = Simulator(agents, scene, clients, event_handler=console_logger)

    # Broadcast a public announcement before starting the simulation
    sim.broadcast(
        PublicEvent(
            "News: A new study suggests AI models now match human-level performance in several creative writing benchmarks."
        )
    )

    sim.run(num_rounds=5)
    print(sim.get_transcript())


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
                    "send_message",
                    "yield",
                    "start_voting",
                    "request_brief",
                    "voting_status",
                    "get_rounds",
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
                    "send_message",
                    "yield",
                    "vote",
                    "voting_status",
                    "get_rounds",
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
                    "send_message",
                    "yield",
                    "vote",
                    "voting_status",
                    "get_rounds",
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
                    "send_message",
                    "yield",
                    "vote",
                    "voting_status",
                    "get_rounds",
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
                    "send_message",
                    "yield",
                    "vote",
                    "voting_status",
                    "get_rounds",
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
    sim.run(num_rounds=15)
    print(sim.get_transcript())


def run_village():
    print("=== VillageScene ===")
    agents = [
        Agent.from_dict(
            {
                "name": "Elias Thorne",
                "user_profile": "You are Elias Thorne, a reclusive scholar living in a remote village. You are deeply knowledgeable about local history, folklore, and ancient ruins. You spend most of your time in your library, poring over old maps and texts. You are logical, reserved, and slightly suspicious of outsiders.",
                "style": "academic and precise",
                "initial_instruction": "You have just discovered a cryptic passage in an old manuscript that hints at a hidden artifact somewhere in the village. Your goal is to decipher the clue and find the artifact.",
                "role_prompt": "Your focus is on research and investigation. Use your knowledge to guide your actions.",
                "action_space": [
                    "send_message",
                    "talk_to",
                    "yield",
                    "move_to_location",
                    "look_around",
                    "gather_resource",
                    "rest",
                ],
                "properties": {"location": (3, 3)},
            }
        ),
        Agent.from_dict(
            {
                "name": "Seraphina",
                "user_profile": "You are Seraphina, the village herbalist. You have an intimate connection with the natural world and possess a deep understanding of plants and their properties. You are compassionate, intuitive, and respected by the villagers for your healing skills. You live in a small cottage near the forest.",
                "style": "gentle and mystical",
                "initial_instruction": "You've noticed a strange wilting of the silverleaf plants near the ancient ruins. You believe it's a sign of a magical imbalance. Your goal is to diagnose the cause and restore balance to the area.",
                "role_prompt": "Your actions should be guided by your connection to nature and your desire to maintain harmony.",
                "action_space": [
                    "send_message",
                    "talk_to",
                    "yield",
                    "move_to_location",
                    "look_around",
                    "gather_resource",
                    "rest",
                ],
                "properties": {"location": (18, 12)},
            }
        ),
        Agent.from_dict(
            {
                "name": "Kaelen",
                "user_profile": "You are Kaelen, the village blacksmith. You are a person of few words but immense skill. Your forge is the heart of the village, where you craft tools, weapons, and intricate metalwork. You are stoic, practical, and fiercely protective of your community.",
                "style": "terse and direct",
                "initial_instruction": "The village's well pump has broken, and you need a rare iron ore to forge a replacement part. The ore is said to be found in the caves to the north. Your goal is to retrieve the ore and repair the pump.",
                "role_prompt": "You are a problem-solver. Focus on practical tasks and the needs of the village.",
                "action_space": [
                    "send_message",
                    "talk_to",
                    "yield",
                    "move_to_location",
                    "look_around",
                    "gather_resource",
                    "rest",
                ],
                "properties": {"location": (10, 8)},
            }
        ),
        Agent.from_dict(
            {
                "name": "Lyra",
                "user_profile": "You are Lyra, a young and adventurous cartographer. You are new to the village, drawn by tales of its mysterious surroundings. You are curious, energetic, and eager to map the uncharted territories around the village.",
                "style": "enthusiastic and inquisitive",
                "initial_instruction": "You've heard rumors of a hidden waterfall deep in the forest. Your goal is to find it and add it to your map of the region.",
                "role_prompt": "Your primary drive is exploration and discovery. Document your findings and interact with others to gather information.",
                "action_space": [
                    "send_message",
                    "talk_to",
                    "yield",
                    "move_to_location",
                    "look_around",
                    "gather_resource",
                    "rest",
                ],
                "properties": {"location": (15, 15)},
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

    sim.broadcast(
        PublicEvent(
            "A traveler passing through the village square mentions a faint, melodic humming sound coming from the direction of the ancient ruins at night."
        )
    )

    sim.run(num_rounds=5)
    print(sim.get_transcript())


if __name__ == "__main__":
    run_simple_chat()
    # run_council()
    # run_village()
