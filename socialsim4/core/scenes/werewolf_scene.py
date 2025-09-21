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
        # Simulation clock (optional)
        self.state.setdefault("time", 0)
        # Phases and counters
        self.state.setdefault("phase", "night")  # night | day_discussion | day_voting
        self.state.setdefault("day_count", 0)
        self.moderator_names = set(moderator_names or [])

        # Roles and life state
        self.state.setdefault("roles", role_map or {})
        self.state.setdefault("alive", [])

        # Voting and night actions
        self.state.setdefault("night_kill_votes", {})
        self.state.setdefault("lynch_votes", {})
        self.state.setdefault("witch_uses", {})  # per-witch: {heals_left, poisons_left}
        self.state.setdefault("witch_saved", False)
        self.state.setdefault("witch_actions", {})  # per-witch: {poison_target}

        # Night turn tracking
        self.state.setdefault("night_spoken", [])

        # End flag
        self.state.setdefault("complete", False)
        self.state.setdefault("winner", None)

    # ----------------- Prompt content -----------------
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

    # ----------------- Scene wiring -----------------
    def initialize_agent(self, agent: Agent):
        # Mark all non-moderator agents as alive on join
        alive = self.state.setdefault("alive", [])
        if agent.name not in alive and not self.is_moderator(agent.name):
            alive.append(agent.name)

        # Assume agent properties already define their role if any; populate scene roles accordingly
        roles = self.state.setdefault("roles", {})
        if agent.name not in roles:
            role = (agent.properties or {}).get("role")
            if role:
                roles[agent.name] = role

    def get_scene_actions(self, agent: Agent):
        # Provide common actions to all agents; role-specific actions should be
        # assigned externally (e.g., in scripts) so the scene stays generic.
        return [
            SpeakAction(),
            VoteLynchAction(),
            YieldAction(),
        ]

    # ----------------- Core helpers -----------------

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

    # ----------------- Messaging -----------------
    def deliver_message(self, event: Event, sender: Agent, simulator: Simulator):
        phase = self.state.get("phase")

        time = self.state.get("time")
        formatted = event.to_string(time)

        recipients: List[str] = []
        if phase == "night":
            # Night chat restricted to werewolves
            for agent in simulator.agents.values():
                if agent.name == sender.name:
                    continue
                if self.is_moderator(sender.name):
                    # Moderator speaks to all living
                    if self._is_alive(agent.name):
                        agent.append_env_message(formatted)
                        recipients.append(agent.name)
                elif (
                    self._is_alive(agent.name) and self._role(agent.name) == "werewolf"
                ):
                    agent.append_env_message(formatted)
                    recipients.append(agent.name)
        else:  # day phases
            for agent in simulator.agents.values():
                if agent.name == sender.name:
                    continue
                if self._is_alive(agent.name) or self.is_moderator(agent.name):
                    agent.append_env_message(formatted)
                    recipients.append(agent.name)

        # Sender sees their own accepted message
        sender.append_env_message(formatted)

        simulator.record_log(
            formatted,
            sender=sender.name,
            recipients=recipients,
            kind=event.__class__.__name__,
        )

    # ----------------- Phase resolution (turn-driven) -----------------
    def post_turn(self, agent: Agent, simulator: Simulator):
        # Advance time via base rule
        super().post_turn(agent, simulator)

        phase = self.state.get("phase")

        if phase == "night":
            # Resolve night after witch has had a chance to act
            self.state["night_spoken"].append(agent.name)

            if len(self.state["night_spoken"]) == len(self.state["roles"]) + 1:
                self._resolve_night(simulator)
                self.state["night_spoken"] = []

    def _resolve_night(self, simulator: Simulator):
        # Compute intended kill target from wolves' votes
        votes: Dict[str, str] = self.state.get("night_kill_votes", {})
        # Only count votes from alive werewolves
        filtered = {
            voter: target
            for voter, target in votes.items()
            if self._is_alive(voter) and self._role(voter) == "werewolf"
        }
        victim: Optional[str] = None
        # First night rule: no wolf kills
        first_night = self.state.get("day_count", 0) == 0
        if filtered:
            counts = Counter(filtered.values())
            top = counts.most_common(1)[0]
            if top:
                candidate = top[0]
                # Must be alive and not a werewolf
                if (
                    (not first_night)
                    and self._is_alive(candidate)
                    and self._role(candidate) != "werewolf"
                ):
                    victim = candidate

        # Witch save and poison
        saved = bool(self.state.get("witch_saved", False))
        poison_targets = []
        for _, action in self.state.get("witch_actions", {}).items():
            tgt = action.get("poison_target")
            if tgt and self._is_alive(tgt):
                poison_targets.append(tgt)

        deaths: List[str] = []
        # Apply victim if not saved
        if victim and not saved:
            deaths.append(victim)
        # Apply poison
        for t in poison_targets:
            if t not in deaths:
                deaths.append(t)

        # Resolve deaths
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

        # Clear night state and switch to day
        self.state["night_kill_votes"] = {}
        self.state["witch_saved"] = False
        self.state["witch_actions"] = {}
        self.state["phase"] = "day_discussion"
        self.state["day_count"] = self.state.get("day_count", 0) + 1
        self.state["lynch_votes"] = {}

        # Check win condition after deaths; if not over, announce the new day with order and rule
        if self._check_win():
            winner = self.state.get("winner")
            simulator.broadcast(PublicEvent(f"Game over: {winner} win."))
            self.state["complete"] = True
        else:
            # Determine speaking order (alive, non-moderators) based on current simulator order
            self.state["day_spoken"] = []

    def _has_majority_vote(self) -> bool:
        votes = self.state.get("lynch_votes", {})
        alive_voters = [v for v in votes.keys() if self._is_alive(v)]
        if not alive_voters:
            return False
        counts = Counter(
            [t for v, t in votes.items() if self._is_alive(v) and self._is_alive(t)]
        )
        if not counts:
            return False
        need = len([n for n in self._alive()]) // 2 + 1
        return any(c >= need for _, c in counts.items())

    def _resolve_lynch(self, simulator: Simulator, prefer_plurality: bool = True):
        votes: Dict[str, str] = self.state.get("lynch_votes", {})
        filtered = {
            voter: target
            for voter, target in votes.items()
            if self._is_alive(voter) and self._is_alive(target)
        }
        lynched: Optional[str] = None
        if filtered:
            counts = Counter(filtered.values())
            need = len(self._alive()) // 2 + 1
            # Majority first
            for target, cnt in counts.items():
                if cnt >= need:
                    lynched = target
                    break
            if lynched is None and prefer_plurality and counts:
                most = counts.most_common()
                if len(most) == 1 or (len(most) > 1 and most[0][1] > most[1][1]):
                    lynched = most[0][0]
        if lynched and self._is_alive(lynched):
            self.state["alive"].remove(lynched)
            simulator.broadcast(
                PublicEvent(f"By vote, {lynched} was lynched. Night begins.")
            )
        else:
            simulator.broadcast(PublicEvent("No lynch today. Night begins."))

    # ----------------- Status & metadata -----------------
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
                # Provide likely victim information based on current wolf votes
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
            if role == "werewolf":
                tips.append("Coordinate with wolves and cast night_kill.")
            elif role == "seer":
                tips.append("Use inspect on one player.")
            elif role == "witch":
                tips.append(
                    "You may witch_save tonight's victim and/or witch_poison another player (each once)."
                )
            else:
                tips.append("Stay quiet at night; await day.")
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

    def to_dict(self):
        base = super().to_dict()
        base.update(
            {
                "phase": self.state.get("phase"),
                "day_count": self.state.get("day_count"),
                "roles": self.state.get("roles", {}),
                "alive": self.state.get("alive", []),
                "witch_uses": self.state.get("witch_uses", {}),
                "type": self.TYPE,
                "moderators": list(self.moderator_names),
            }
        )
        return base

    @classmethod
    def from_dict(cls, data):
        scene = cls(
            name=data.get("name", "WerewolfScene"),
            initial_event=data.get("initial_event", ""),
            role_map=data.get("roles", {}),
            moderator_names=data.get("moderators", []),
        )
        scene.state.update(
            {
                "phase": data.get("phase", "night"),
                "day_count": data.get("day_count", 0),
                "roles": data.get("roles", {}),
                "alive": data.get("alive", []),
                "witch_uses": data.get("witch_uses", {}),
            }
        )
        return scene
