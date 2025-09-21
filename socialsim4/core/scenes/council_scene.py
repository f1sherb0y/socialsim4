from socialsimv4.core.actions.council_actions import (
    GetRoundsAction,
    StartVotingAction,
    VoteAction,
    VotingStatusAction,
)
from socialsimv4.core.agent import Agent
from socialsimv4.core.event import PublicEvent
from socialsimv4.core.scenes.simple_chat_scene import SimpleChatScene


class CouncilScene(SimpleChatScene):
    TYPE = "council_scene"

    def __init__(self, name, initial_event):
        super().__init__(name, initial_event)
        self.state["votes"] = {}
        self.state["voting_started"] = False
        self.state["voting_completed_announced"] = False
        self.complete = False

    def get_scene_actions(self, agent: Agent):
        actions = super().get_scene_actions(agent)
        # Common council actions for all agents
        actions.append([GetRoundsAction(), VotingStatusAction()])
        return actions

    def get_behavior_guidelines(self):
        base = super().get_behavior_guidelines()
        return (
            base
            + """
- While you have your own views, you may occasionally shift your opinion slightly if presented with compelling arguments, though it's not necessary. Once voting starts, cast your vote.
- Participate actively in discussions, vote when appropriate, and follow the host's lead.
"""
        )

    def is_complete(self):
        return self.complete

    def post_round(self, simulator):
        # After each full round (all agents had a turn), if voting started and
        # all non-host members have voted, broadcast completion once.
        if not self.state.get("voting_started", False):
            return
        if self.state.get("voting_completed_announced", False):
            return

        num_members = sum(1 for a in simulator.agents.values() if a.name != "Host")
        votes = self.state.get("votes", {})
        if len(votes) >= num_members and num_members > 0:
            yes = sum(v == "yes" for v in votes.values())
            no = sum(v == "no" for v in votes.values())
            abstain = sum(v == "abstain" for v in votes.values())
            result = "passed" if yes > num_members / 2 else "failed"
            simulator.broadcast(
                PublicEvent(
                    f"Voting on the draft has concluded. It {result} with {yes} yes, {no} no, and {abstain} abstain."
                )
            )
            self.state["voting_completed_announced"] = True
            self.complete = True
            self.log("Voting result announced automatically after round.")
