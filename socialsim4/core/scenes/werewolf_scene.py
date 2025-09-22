from collections import Counter
from typing import Dict, List, Optional, Tuple

from socialsim4.core.actions.base_actions import SpeakAction, YieldAction
from socialsim4.core.actions.werewolf_actions import VoteLynchAction
from socialsim4.core.agent import Agent
from socialsim4.core.event import Event, PublicEvent
from socialsim4.core.scene import Scene
from socialsim4.core.simulator import Simulator


class WerewolfScene(Scene):
    TYPE = "werewolf_scene"

    def __init__(
        self,
        name: str,
        initial_event: str,
        role_map: Optional[Dict[str, str]] = None,
        moderator_names: Optional[List[str]] = None,
    ):
        super().__init__(name, initial_event)
        self.moderator_names = set(moderator_names or [])
        s = self.state
        s.update(
            {
                "time": s.get("time", 0),
                "phase": s.get("phase", "night"),  # night | day_discussion | day_voting
                "day_count": s.get("day_count", 0),
                "roles": s.get("roles", role_map or {}),
                "alive": s.get("alive", []),
                "night_kill_votes": s.get("night_kill_votes", {}),
                "lynch_votes": s.get("lynch_votes", {}),
                "witch_uses": s.get("witch_uses", {}),
                "witch_saved": s.get("witch_saved", False),
                "witch_actions": s.get("witch_actions", {}),
                "night_spoken": s.get("night_spoken", []),
                "complete": s.get("complete", False),
                "winner": s.get("winner", None),
            }
        )

    def get_scenario_description(self):
        return (
            "You are playing a Werewolf social deduction game with night and day cycles. "
            "During the day, there are two phases: discussion then voting (the Moderator opens/closes voting). "
            "At night, werewolves coordinate to eliminate one player; the Seer may inspect; the Witch may save or poison (each potion once)."
        )

    def get_behavior_guidelines(self):
        return (
            "- If you are a Werewolf: coordinate subtly, avoid revealing yourselves, and vote at night. You have ONLY one chance to speak and vote during night.\n"
            "- If you are the Seer: inspect wisely at night and decide how to influence the day discussion without outing yourself.\n"
            "- If you are the Witch: consider saving the victim and poisoning strategically; you have each potion once.\n"
            "- If you are a Villager: reason from discussion and voting patterns; avoid chaos.\n"
            "- At night, ONLY werewolves are allowed to speak.\n"
            "- First night: werewolves should not kill.\n"
            "- Each night, werewolves can vote together to kill one player.\n"
            "- During day discussion, each player may speak exactly once; follow the published speaking order; answer questions addressed to you succinctly.\n"
            "- During day voting, players are not allowed to speak. Before yielding your turn, cast a lynch vote.\n"
        )

    def initialize_agent(self, agent: Agent):
        alive = self.state.setdefault("alive", [])
        if agent.name not in alive and not self.is_moderator(agent.name):
            alive.append(agent.name)
        roles = self.state.setdefault("roles", {})
        if agent.name not in roles:
            role = (agent.properties or {}).get("role")
            if role:
                roles[agent.name] = role

    def get_scene_actions(self, agent: Agent):
        return [
            SpeakAction(),
            VoteLynchAction(),
            YieldAction(),
        ]

    def _alive(self) -> List[str]:
        return list(self.state.get("alive", []))

    def _is_alive(self, name: str) -> bool:
        return name in self.state.get("alive", [])

    def _role(self, name: str) -> Optional[str]:
        return self.state.get("roles", {}).get(name)

    def _count_roles(self) -> Tuple[int, int]:
        alive = self._alive()
        wolves = sum(1 for n in alive if self._role(n) == "werewolf")
        villagers = len(alive) - wolves
        return wolves, villagers

    def _check_win(self):
        wolves, villagers = self._count_roles()
        if wolves == 0 and villagers == 0:
            self.state["complete"] = True
            self.state["winner"] = "no one"
            return True
        if wolves == 0:
            self.state["complete"] = True
            self.state["winner"] = "villagers"
            return True
        if villagers == 0:
            self.state["complete"] = True
            self.state["winner"] = "werewolves"
            return True
        return False

    def deliver_message(self, event: Event, sender: Agent, simulator: Simulator):
        phase = self.state.get("phase")
        formatted = event.to_string(self.state.get("time"))
        recipients: List[str] = []
        mod_sender = self.is_moderator(sender.name)
        for a in simulator.agents.values():
            if a.name == sender.name:
                continue
            ok = (
                phase == "night"
                and (
                    (mod_sender and self._is_alive(a.name))
                    or (self._is_alive(a.name) and self._role(a.name) == "werewolf")
                )
            ) or (
                phase != "night"
                and (self._is_alive(a.name) or self.is_moderator(a.name))
            )
            if ok:
                a.add_env_feedback(formatted)
                recipients.append(a.name)
        sender.add_env_feedback(formatted)
        simulator.record_log(
            formatted,
            sender=sender.name,
            recipients=recipients,
            kind=event.__class__.__name__,
        )

    def post_turn(self, agent: Agent, simulator: Simulator):
        super().post_turn(agent, simulator)
        phase = self.state.get("phase")
        if phase == "night":
            self.state["night_spoken"].append(agent.name)
            if len(self.state["night_spoken"]) == len(self.state["roles"]) + 1:
                self._resolve_night(simulator)
                self.state["night_spoken"] = []

    def _resolve_night(self, simulator: Simulator):
        votes: Dict[str, str] = self.state.get("night_kill_votes", {})
        filtered = {
            v: t
            for v, t in votes.items()
            if self._is_alive(v) and self._role(v) == "werewolf"
        }
        victim: Optional[str] = None
        first_night = self.state.get("day_count", 0) == 0
        if filtered:
            counts = Counter(filtered.values())
            candidate = counts.most_common(1)[0][0]
            if (
                (not first_night)
                and self._is_alive(candidate)
                and self._role(candidate) != "werewolf"
            ):
                victim = candidate
        saved = bool(self.state.get("witch_saved", False))
        poison_targets = [
            a["poison_target"]
            for a in self.state.get("witch_actions", {}).values()
            if a.get("poison_target") and self._is_alive(a["poison_target"])
        ]
        deaths: List[str] = [victim] if victim and not saved else []
        deaths += [t for t in poison_targets if t not in deaths]
        if deaths:
            for d in deaths:
                if self._is_alive(d):
                    self.state["alive"].remove(d)
            if len(deaths) == 1:
                simulator.broadcast(
                    PublicEvent(f"The night ends. At dawn, {deaths[0]} was found dead.")
                )
            else:
                simulator.broadcast(
                    PublicEvent(
                        "The night ends. At dawn, multiple bodies were found: "
                        + ", ".join(deaths)
                    )
                )
        else:
            simulator.broadcast(PublicEvent("The night ends. At dawn, no one died."))
        self.state["night_kill_votes"] = {}
        self.state["witch_saved"] = False
        self.state["witch_actions"] = {}
        self.state["phase"] = "day_discussion"
        self.state["day_count"] = self.state.get("day_count", 0) + 1
        self.state["lynch_votes"] = {}
        if self._check_win():
            winner = self.state.get("winner")
            simulator.broadcast(PublicEvent(f"Game over: {winner} win."))
            self.state["complete"] = True
        else:
            self.state["day_spoken"] = []

    def _resolve_lynch(self, simulator: Simulator, prefer_plurality: bool = True):
        counts = Counter(
            t
            for v, t in self.state.get("lynch_votes", {}).items()
            if self._is_alive(v) and self._is_alive(t)
        )
        lynched: Optional[str] = None
        if counts:
            need = len(self._alive()) // 2 + 1
            lynched = next((t for t, c in counts.items() if c >= need), None)
            if lynched is None and prefer_plurality:
                top2 = counts.most_common(2)
                if top2 and (len(top2) == 1 or top2[0][1] > top2[1][1]):
                    lynched = top2[0][0]
        if lynched:
            self.state["alive"].remove(lynched)
            simulator.broadcast(
                PublicEvent(f"By vote, {lynched} was lynched. Night begins.")
            )
        else:
            simulator.broadcast(PublicEvent("No lynch today. Night begins."))

    def get_agent_status_prompt(self, agent: Agent) -> str:
        role = self._role(agent.name) or (
            "moderator" if self.is_moderator(agent.name) else "(unknown)"
        )
        phase = self.state.get("phase", "night")
        day = self.state.get("day_count", 0)
        alive = self._is_alive(agent.name)
        uses = self.state.get("witch_uses", {}).get(agent.name, {})
        extra_lines = []
        if role == "witch":
            extra_lines.append(
                f"Potions left (save/poison): {uses.get('heals_left', 0)}/{uses.get('poisons_left', 0)}"
            )
            if phase == "night":
                votes = self.state.get("night_kill_votes", {})
                filtered = {
                    v: t
                    for v, t in votes.items()
                    if self._is_alive(v) and self._role(v) == "werewolf"
                }
                likely = None
                if filtered:
                    most = Counter(filtered.values()).most_common(1)
                    if most:
                        likely = most[0][0]
                extra_lines.append(
                    f"Likely victim (so far): {likely if likely else 'unknown'}"
                )
        tips = []
        if not alive:
            tips.append("You are dead. You cannot act or speak.")
        elif phase == "night":
            tips_map = {
                "werewolf": "Coordinate with wolves and cast night_kill.",
                "seer": "Use inspect on one player.",
                "witch": "You may witch_save tonight's victim and/or witch_poison another player (each once).",
            }
            tips.append(tips_map.get(role, "Stay quiet at night; await day."))
        elif phase == "day_discussion":
            tips.append("Discuss. Moderator will open voting.")
        elif phase == "day_voting":
            votes = self.state.get("lynch_votes", {})
            if agent.name in votes and alive:
                tips.append(
                    f"Your vote: {votes.get(agent.name)}. You may revote or yield."
                )
            else:
                tips.append("You haven't voted yet; cast your vote with vote_lynch.")
        tip_text = " ".join(tips)
        extra = ("\n" + "\n".join(extra_lines)) if extra_lines else ""
        return f"--- Status ---\nPhase: {phase} (day {day})\nAlive: {alive}\n{tip_text}{extra}\n"

    def is_moderator(self, name: str) -> bool:
        return name in self.moderator_names or name.lower() == "moderator"

    def should_skip_turn(self, agent: Agent, simulator: Simulator) -> bool:
        phase = self.state.get("phase")
        if self.is_moderator(agent.name):
            return False
        if not self._is_alive(agent.name):
            return True
        if phase == "night":
            role = self._role(agent.name)
            return role not in ("werewolf", "seer", "witch")
        return False

    def is_complete(self):
        return bool(self.state.get("complete", False))

    # ----- Unified serialization hooks -----
    def serialize_config(self) -> dict:
        return {
            "moderators": list(self.moderator_names),
        }

    @classmethod
    def deserialize_config(cls, config: Dict) -> Dict:
        return {
            "moderator_names": config.get("moderators", []),
        }
