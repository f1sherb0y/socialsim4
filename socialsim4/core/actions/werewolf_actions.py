from typing import Optional

from socialsim4.core.action import Action
from socialsim4.core.event import PublicEvent


def _is_alive(scene, name: str) -> bool:
    return name in scene.state.get("alive", [])


def _role_of(scene, name: str) -> Optional[str]:
    return scene.state.get("roles", {}).get(name)


class VoteLynchAction(Action):
    NAME = "vote_lynch"
    DESC = "During the day, vote to lynch a player. One vote per day."
    INSTRUCTION = """- To vote to lynch someone during the day:
<Action name=\"vote_lynch\"><target>[player_name]</target></Action>
"""

    def handle(self, action_data, agent, simulator, scene):
        if scene.state.get("phase") != "day_voting":
            agent.append_env_message("You can only vote during the voting phase.")
            return False
        if not _is_alive(scene, agent.name):
            agent.append_env_message("You are dead and cannot act.")
            return False
        target = action_data.get("target")
        if not target or not _is_alive(scene, target):
            agent.append_env_message("Provide a living 'target' to vote.")
            return False

        votes = scene.state.setdefault("lynch_votes", {})
        votes[agent.name] = target
        tally = sum(1 for v, t in votes.items() if t == target and _is_alive(scene, v))
        simulator.record_log(
            f"{agent.name} voted to lynch {target} (tally: {tally})",
            sender=agent.name,
            recipients=[n for n in scene.state.get("alive", []) if n != agent.name],
            kind="vote_lynch",
        )
        simulator.broadcast(PublicEvent(f"{agent.name} voted to lynch {target}."))
        return True


class NightKillAction(Action):
    NAME = "night_kill"
    DESC = "At night, werewolves vote on a victim to kill."
    INSTRUCTION = """- Werewolves: to vote a night kill target (at night only):
<Action name=\"night_kill\"><target>[player_name]</target></Action>
"""

    def handle(self, action_data, agent, simulator, scene):
        if scene.state.get("phase") != "night":
            agent.append_env_message("Night kill can only be cast at night.")
            return False
        if (not _is_alive(scene, agent.name)) or _role_of(
            scene, agent.name
        ) != "werewolf":
            agent.append_env_message("Only living werewolves can vote a night kill.")
            return False
        if scene.state.get("day_count", 0) == 0:
            agent.append_env_message(
                "First night has no kills; discuss with fellow wolves."
            )
            return False
        target = action_data.get("target")
        if (
            (not target)
            or (not _is_alive(scene, target))
            or _role_of(scene, target) == "werewolf"
        ):
            agent.append_env_message("Provide a living non-werewolf 'target'.")
            return False

        votes = scene.state.setdefault("night_kill_votes", {})
        votes[agent.name] = target
        # Private confirmation
        agent.append_env_message(f"Night kill vote recorded: {target}.")
        tally = sum(
            1
            for v, t in votes.items()
            if t == target and _is_alive(scene, v) and _role_of(scene, v) == "werewolf"
        )
        simulator.record_log(
            f"{agent.name} cast night_kill vote: {target} (tally: {tally})",
            sender=agent.name,
            recipients=None,
            kind="night_kill",
        )
        return True


class InspectAction(Action):
    NAME = "inspect"
    DESC = "At night, seer inspects a player and learns if they are a werewolf."
    INSTRUCTION = """- Seer: to inspect a player at night:
<Action name=\"inspect\"><target>[player_name]</target></Action>
"""

    def handle(self, action_data, agent, simulator, scene):
        if scene.state.get("phase") != "night":
            agent.append_env_message("You can only inspect at night.")
            return False
        if not _is_alive(scene, agent.name) or _role_of(scene, agent.name) != "seer":
            agent.append_env_message("Only a living Seer can inspect.")
            return False
        target = action_data.get("target")
        if not target or not _is_alive(scene, target):
            agent.append_env_message("Provide a living 'target' to inspect.")
            return False

        is_wolf = _role_of(scene, target) == "werewolf"
        agent.append_env_message(
            f"Inspection result: {target} is {'a werewolf' if is_wolf else 'not a werewolf'}."
        )
        simulator.record_log(
            f"{agent.name} used inspect on {target} (result: {'werewolf' if is_wolf else 'not'})",
            sender=agent.name,
            recipients=None,
            kind="inspect",
        )
        return True


class WitchSaveAction(Action):
    NAME = "witch_save"
    DESC = "At night, witch may save the intended victim once per game."
    INSTRUCTION = """- Witch: to save tonight's victim (once per game):
<Action name=\"witch_save\" />
"""

    def handle(self, action_data, agent, simulator, scene):
        if scene.state.get("phase") != "night":
            agent.append_env_message("You can only use save at night.")
            return False
        if not _is_alive(scene, agent.name) or _role_of(scene, agent.name) != "witch":
            agent.append_env_message("Only a living Witch can save.")
            return False

        uses = scene.state.setdefault("witch_uses", {}).setdefault(
            agent.name, {"heals_left": 1, "poisons_left": 1}
        )
        if uses.get("heals_left", 0) <= 0:
            agent.append_env_message("You have already used your save potion.")
            return False

        scene.state["witch_saved"] = True
        uses["heals_left"] = uses.get("heals_left", 0) - 1
        agent.append_env_message("You prepare the save potion for tonight's victim.")
        simulator.record_log(
            f"{agent.name} used witch_save (victim will be saved)",
            sender=agent.name,
            recipients=None,
            kind="witch_save",
        )
        return True


class WitchPoisonAction(Action):
    NAME = "witch_poison"
    DESC = "At night, witch may poison one player once per game."
    INSTRUCTION = """- Witch: to poison a player at night (once per game):
<Action name=\"witch_poison\"><target>[player_name]</target></Action>
"""

    def handle(self, action_data, agent, simulator, scene):
        if scene.state.get("phase") != "night":
            agent.append_env_message("You can only poison at night.")
            return False
        if not _is_alive(scene, agent.name) or _role_of(scene, agent.name) != "witch":
            agent.append_env_message("Only a living Witch can poison.")
            return False
        target = action_data.get("target")
        if not target or not _is_alive(scene, target) or target == agent.name:
            agent.append_env_message("Provide a living 'target' other than yourself.")
            return False

        uses = scene.state.setdefault("witch_uses", {}).setdefault(
            agent.name, {"heals_left": 1, "poisons_left": 1}
        )
        if uses.get("poisons_left", 0) <= 0:
            agent.append_env_message("You have already used your poison potion.")
            return False

        scene.state.setdefault("witch_actions", {}).setdefault(agent.name, {})[
            "poison_target"
        ] = target
        uses["poisons_left"] = uses.get("poisons_left", 0) - 1
        agent.append_env_message(f"You prepared a poison targeting {target}.")
        simulator.record_log(
            f"{agent.name} used witch_poison on {target}",
            sender=agent.name,
            recipients=None,
            kind="witch_poison",
        )
        return True


class OpenVotingAction(Action):
    NAME = "open_voting"
    DESC = "Moderator opens the voting phase."
    INSTRUCTION = """- Moderator: open voting after discussion:
<Action name=\"open_voting\" />
"""

    def handle(self, action_data, agent, simulator, scene):
        name = agent.name
        if not scene.is_moderator(name):
            agent.append_env_message("Only the moderator can open voting.")
            return False
        if scene.state.get("phase") != "day_discussion":
            agent.append_env_message("Open voting only during discussion phase.")
            return False
        scene.state["phase"] = "day_voting"
        scene.state["lynch_votes"] = {}
        simulator.record_log(f"{name} opened voting", sender=name, kind="open_voting")
        simulator.broadcast(PublicEvent("Voting is now open."))
        return True


class CloseVotingAction(Action):
    NAME = "close_voting"
    DESC = "Moderator closes voting, resolves lynch, ends the day."
    INSTRUCTION = """- Moderator: close voting and end the day:
<Action name=\"close_voting\" />
"""

    def handle(self, action_data, agent, simulator, scene):
        name = agent.name
        if not scene.is_moderator(name):
            agent.append_env_message("Only the moderator can close voting.")
            return False
        if scene.state.get("phase") != "day_voting":
            agent.append_env_message("Close voting only during voting phase.")
            return False
        simulator.record_log(f"{name} closed voting", sender=name, kind="close_voting")
        scene._resolve_lynch(simulator, prefer_plurality=True)
        scene.state["lynch_votes"] = {}
        scene.state["phase"] = "night"
        if scene._check_win():
            winner = scene.state.get("winner")
            simulator.broadcast(PublicEvent(f"Game over: {winner} win."))
        return True
