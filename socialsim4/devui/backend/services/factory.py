from typing import Tuple

from socialsim4.core.simulator import Simulator
from socialsim4.devui.backend.services.snapshots import DevEventBus
from socialsim4.scripts.run_basic_scenes import build_simple_chat_sim, make_clients


def make_sim(scenario: str) -> Tuple[Simulator, DevEventBus, list[str]]:
    if scenario == "simple_chat":
        sim = build_simple_chat_sim()
    else:
        raise ValueError("Unknown scenario: " + scenario)
    bus = DevEventBus()
    # Attach publish handler to sim and agents
    sim.log_event = bus.publish
    for a in sim.agents.values():
        a.log_event = bus.publish
    names = list(sim.agents.keys())
    return sim, bus, names

