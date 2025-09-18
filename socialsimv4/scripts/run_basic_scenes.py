import json
import os
from typing import Dict, List

from socialsimv4.api.schemas import LLMConfig
from socialsimv4.core.agent import Agent
from socialsimv4.core.event import NewsEvent
from socialsimv4.core.llm import create_llm_client
from socialsimv4.core.scenes.council_scene import CouncilScene
from socialsimv4.core.scenes.map_scene import MapScene
from socialsimv4.core.scenes.simple_chat_scene import SimpleChatScene
from socialsimv4.core.scenes.village_scene import VillageScene


def console_logger(event_type: str, data):
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
            model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
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
    # agents = make_agents(["Host", "Alice", "Bob"], ["send_message", "skip_reply"])
    agents = [
        Agent.from_dict(
            {
                "name": "Host",
                "user_profile": "You are the host of a chat room. Your role is to facilitate conversation, introduce topics, and ensure everyone has a chance to speak. You are neutral and objective.",
                "style": "welcoming and clear",
                "action_space": ["send_message", "skip_reply"],
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
                "action_space": ["send_message", "skip_reply"],
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
                "action_space": ["send_message", "skip_reply"],
                "initial_instruction": "",
                "role_prompt": "",
                "properties": {},
            }
        ),
    ]

    scene = SimpleChatScene("room", "Welcome to the chat room.")
    clients = make_clients()

    from socialsimv4.core.simulator import Simulator

    sim = Simulator(agents, scene, clients, event_handler=console_logger)

    # Broadcast a news event before starting the simulation
    sim.broadcast(
        NewsEvent(
            "A new study reveals that AI has surpassed human-level performance in creative writing."
        )
    )

    sim.run(num_rounds=5)
    print(sim.get_transcript())


def run_council():
    print("=== CouncilScene ===")
    agents = make_agents(["Host", "Alice", "Bob"], ["send_message", "skip_reply"])
    scene = CouncilScene("council", "A draft is presented for voting.")
    clients = make_clients()

    from socialsimv4.core.simulator import Simulator

    sim = Simulator(agents, scene, clients, event_handler=console_logger)
    sim.run(num_rounds=3)
    print(sim.get_transcript())


def run_map():
    print("=== MapScene ===")
    agents = make_agents(
        ["Alice", "Bob"],
        [
            "send_message",
            "speak",
            "skip_reply",
            "move_to_location",
            "look_around",
            "gather_resource",
            "rest",
        ],
    )
    scene = MapScene("village", "A new day dawns.", map_width=20, map_height=20)
    clients = make_clients()

    from socialsimv4.core.simulator import Simulator

    sim = Simulator(agents, scene, clients, event_handler=console_logger)
    sim.run(num_rounds=4)
    print(sim.get_transcript())


def run_village():
    print("=== VillageScene ===")
    agents = make_agents(["Alice", "Bob"], ["send_message", "skip_reply"])
    scene = VillageScene("village", "A new day begins.")
    clients = make_clients()

    from socialsimv4.core.simulator import Simulator

    sim = Simulator(agents, scene, clients, event_handler=console_logger)
    sim.run(num_rounds=5)
    print(sim.get_transcript())


if __name__ == "__main__":
    run_simple_chat()
    print()
    # run_council()
    # print()
    # run_map()
    # print()
    # run_village()
