from __future__ import annotations

import asyncio
from typing import Dict

from socialsim4.core.agent import Agent
from socialsim4.core.event import PublicEvent
from socialsim4.core.ordering import ControlledOrdering, CycledOrdering, SequentialOrdering
from socialsim4.core.registry import ACTION_SPACE_MAP, SCENE_ACTIONS, SCENE_MAP
from socialsim4.core.simtree import SimTree
from socialsim4.core.simulator import Simulator
from socialsim4.scenarios.basic import make_clients_from_env


class SimTreeRecord:
    def __init__(self, tree: SimTree):
        self.tree = tree
        self.subs: list[asyncio.Queue] = []
        self.running: set[int] = set()


def _quiet_logger(event_type: str, data: dict) -> None:
    return


def _build_tree_for_scene(scene_type: str, clients: dict | None = None) -> SimTree:
    scene_cls = SCENE_MAP.get(scene_type)
    if scene_cls is None:
        raise ValueError(f"Unsupported scene type: {scene_type}")
    active = clients or make_clients_from_env()
    scene = scene_cls("preview", "")
    agents = [
        # minimal placeholder agent; real agents come from agent_config at runtime
        Agent.deserialize(
            {
                "name": "Alice",
                "user_profile": "",
                "style": "",
                "initial_instruction": "",
                "role_prompt": "",
                "action_space": [],
                "properties": {},
            }
        )
    ]
    sim = Simulator(agents, scene, active, event_handler=_quiet_logger, ordering=SequentialOrdering())
    return SimTree.new(sim, active)


def _apply_agent_config(simulator, agent_config: dict | None):
    if not agent_config:
        return
    items = agent_config.get("agents") or []
    agents_list = list(simulator.agents.values())
    count = min(len(items), len(agents_list))
    # First apply names/profiles by position, then rebuild mapping
    for i in range(count):
        cfg = items[i] or {}
        agent = agents_list[i]
        new_name = str(cfg.get("name") or "").strip()
        if new_name:
            agent.name = new_name
        profile = str(cfg.get("profile") or "").strip()
        if profile:
            agent.user_profile = profile
    # Rebuild agents mapping to reflect renames
    simulator.agents = {a.name: a for a in agents_list}
    # Now apply actions (scene common + selected) per agent
    for i in range(count):
        cfg = items[i] or {}
        agent = agents_list[i]
        selected = [str(a) for a in (cfg.get("action_space") or [])]
        scene_actions = simulator.scene.get_scene_actions(agent) or []
        picked = []
        for key in selected:
            act = ACTION_SPACE_MAP.get(key)
            if act is not None:
                picked.append(act)
        merged = []
        seen: set[str] = set()
        for act in list(scene_actions) + picked:
            n = getattr(act, "NAME", None)
            if n and n not in seen:
                merged.append(act)
                seen.add(n)
        agent.action_space = merged
    # Refresh ordering candidates after renames
    simulator.ordering.set_simulation(simulator)


def _build_tree_for_sim(sim_record, clients: dict | None = None) -> SimTree:
    scene_type = sim_record.scene_type
    scene_cls = SCENE_MAP.get(scene_type)
    if scene_cls is None:
        raise ValueError(f"Unsupported scene type: {scene_type}")

    cfg = getattr(sim_record, "scene_config", {}) or {}
    name = getattr(sim_record, "name", scene_type)

    # Build scene via constructor based on type
    if scene_type == "simple_chat_scene":
        # Use generalized initial events; constructor initial can be empty
        scene = scene_cls(name, "")
    elif scene_type == "council_scene":
        draft = str(cfg.get("draft_text") or "")
        scene = scene_cls(name, "")
    elif scene_type == "village_scene":
        from socialsim4.core.scenes.village_scene import GameMap

        map_data = cfg.get("map")
        game_map = GameMap.deserialize(map_data)
        movement_cost = int(cfg.get("movement_cost", 1))
        chat_range = int(cfg.get("chat_range", 5))
        print_map_each_turn = bool(cfg.get("print_map_each_turn", False))
        scene = scene_cls(name, "Welcome to the village.", game_map=game_map, movement_cost=movement_cost, chat_range=chat_range, print_map_each_turn=print_map_each_turn)
    elif scene_type == "landlord_scene":
        num_decks = int(cfg.get("num_decks", 1))
        seed = cfg.get("seed")
        seed_int = int(seed) if seed is not None else None
        scene = scene_cls(name, "New game: Dou Dizhu.", seed=seed_int, num_decks=num_decks)
    elif scene_type == "werewolf_scene":
        initial = str(cfg.get("initial_event") or "Welcome to Werewolf.")
        role_map = cfg.get("role_map") or None
        moderator_names = cfg.get("moderator_names") or None
        scene = scene_cls(name, initial, role_map=role_map, moderator_names=moderator_names)
    else:
        scene = scene_cls(name, str(cfg.get("initial_event") or ""))

    # Build agents from agent_config
    items = (getattr(sim_record, "agent_config", {}) or {}).get("agents") or []
    built_agents = []
    for cfg_agent in items:
        aname = str(cfg_agent.get("name") or "").strip() or "Agent"
        profile = str(cfg_agent.get("profile") or "")
        selected = [str(a) for a in (cfg_agent.get("action_space") or [])]
        # scene common actions from registry (fallback to scene introspection)
        reg = SCENE_ACTIONS.get(scene_type)
        basic_names = list(reg.get("basic", []))

        seen = set()
        merged_names = []
        for n in basic_names + selected:
            if n and n not in seen:
                seen.add(n)
                merged_names.append(n)
        built_agents.append(
            Agent.deserialize(
                {
                    "name": aname,
                    "user_profile": profile,
                    "style": "",
                    "initial_instruction": "",
                    "role_prompt": "",
                    "action_space": merged_names,
                    "properties": {},
                }
            )
        )

    ordering = SequentialOrdering()
    if scene_type == "landlord_scene":

        def next_active(sim):
            s = sim.scene
            p = s.state.get("phase")
            if p == "bidding":
                if s.state.get("bidding_stage") == "call":
                    i = s.state.get("bid_turn_index")
                    return (s.state.get("players") or [None])[i]
                elig = list(s.state.get("rob_eligible") or [])
                acted = dict(s.state.get("rob_acted") or {})
                if not elig:
                    return None
                names = list(s.state.get("players") or [])
                start = s.state.get("bid_turn_index", 0)
                for off in range(len(names)):
                    idx = (start + off) % len(names)
                    name = names[idx]
                    if name in elig and not acted.get(name, False):
                        return name
                return None
            if p == "doubling":
                order = list(s.state.get("doubling_order") or [])
                acted = dict(s.state.get("doubling_acted") or {})
                for name in order:
                    if not acted.get(name, False):
                        return name
                return None
            if p == "playing":
                players = s.state.get("players") or []
                idx = s.state.get("current_turn", 0)
                if players:
                    return players[idx % len(players)]
            return None

        ordering = ControlledOrdering(next_fn=next_active)
    elif scene_type == "werewolf_scene":
        # Build cycled schedule similar to scenario builder
        roles = cfg.get("role_map") or {}
        names = [a.name for a in built_agents]
        wolves = [n for n in names if roles.get(n) == "werewolf"]
        witches = [n for n in names if roles.get(n) == "witch"]
        seers = [n for n in names if roles.get(n) == "seer"]
        seq = wolves + wolves + seers + witches + names + names + ["Moderator"]
        ordering = CycledOrdering(seq)

    sim = Simulator(
        built_agents,
        scene,
        clients or make_clients_from_env(),
        event_handler=_quiet_logger,
        ordering=ordering,
        max_steps_per_turn=3 if scene_type == "landlord_scene" else 5,
    )
    # Broadcast configured initial events as public events
    for text in cfg.get("initial_events") or []:
        if isinstance(text, str) and text.strip():
            sim.broadcast(PublicEvent(text))
    # For council, include draft announcement as an initial event if provided
    if scene_type == "council_scene":
        draft = str(cfg.get("draft_text") or "").strip()
        if draft:
            sim.broadcast(PublicEvent(f"The chamber will now consider the following draft for debate and vote:\n{draft}"))
    return SimTree.new(sim, sim.clients)


class SimTreeRegistry:
    def __init__(self) -> None:
        self._records: Dict[str, SimTreeRecord] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, simulation_id: str, scene_type: str, clients: dict | None = None) -> SimTreeRecord:
        key = simulation_id.upper()
        record = self._records.get(key)
        if record is not None:
            return record
        async with self._lock:
            record = self._records.get(key)
            if record is not None:
                return record
            tree = await asyncio.to_thread(_build_tree_for_scene, scene_type, clients)
            record = SimTreeRecord(tree)
            # Wire event loop for thread-safe fanout
            loop = asyncio.get_running_loop()
            tree.attach_event_loop(loop)

            # Forward all node log events to tree-level subscribers (only for running nodes)
            def _fanout(event: dict) -> None:
                if int(event.get("node", -1)) not in record.running:
                    return
                for q in list(record.subs):
                    loop.call_soon_threadsafe(q.put_nowait, event)

            tree.set_tree_broadcast(_fanout)
            self._records[key] = record
            return record

    async def get_or_create_from_sim(self, sim_record, clients: dict | None = None) -> SimTreeRecord:
        key = sim_record.id.upper()
        record = self._records.get(key)
        if record is not None:
            return record
        async with self._lock:
            record = self._records.get(key)
            if record is not None:
                return record
            tree = await asyncio.to_thread(_build_tree_for_sim, sim_record, clients)
            record = SimTreeRecord(tree)
            loop = asyncio.get_running_loop()
            tree.attach_event_loop(loop)

            def _fanout(event: dict) -> None:
                if int(event.get("node", -1)) not in record.running:
                    return
                for q in list(record.subs):
                    loop.call_soon_threadsafe(q.put_nowait, event)

            tree.set_tree_broadcast(_fanout)
            self._records[key] = record
            return record

    def remove(self, simulation_id: str) -> None:
        self._records.pop(simulation_id.upper(), None)

    def get(self, simulation_id: str) -> SimTreeRecord | None:
        return self._records.get(simulation_id.upper())


SIM_TREE_REGISTRY = SimTreeRegistry()
