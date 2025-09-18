from socialsimv4.core.actions.council_actions import (
    GetVotingResultAction,
    StartVotingAction,
    VoteAction,
)
from socialsimv4.core.agent import Agent
from socialsimv4.core.scenes.simple_chat_scene import SimpleChatScene


class CouncilScene(SimpleChatScene):
    TYPE = "council_scene"
    def __init__(self, name, initial_event):
        super().__init__(name, initial_event)
        self.state["votes"] = {}
        self.state["voting_started"] = False
        self.complete = False

    def initialize_agent(self, agent: Agent):
        super().initialize_agent(agent)
        agent.action_space.extend(
            [
                VoteAction(),
                StartVotingAction(),
                GetVotingResultAction(),
            ]
        )

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
