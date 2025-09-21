from .actions.base_actions import SendMessageAction, TalkToAction, YieldAction
from .actions.council_actions import (
    GetRoundsAction,
    RequestBriefAction,
    StartVotingAction,
    VoteAction,
    VotingStatusAction,
)
from .actions.village_actions import (
    # ExploreAction,
    GatherResourceAction,
    LookAroundAction,
    MoveToLocationAction,
    # QuickMoveAction,
    RestAction,
)
from .actions.web_actions import WebSearchAction, ViewPageAction
from .scenes.council_scene import CouncilScene
from .scenes.simple_chat_scene import SimpleChatScene
from .scenes.village_scene import VillageScene

ACTION_SPACE_MAP = {
    "send_message": SendMessageAction(),
    # "speak": removed in favor of targeted talk_to
    "talk_to": TalkToAction(),
    "yield": YieldAction(),
    "move_to_location": MoveToLocationAction(),
    "look_around": LookAroundAction(),
    "gather_resource": GatherResourceAction(),
    "rest": RestAction(),
    # "quick_move": QuickMoveAction(),
    # "explore": ExploreAction(),
    "start_voting": StartVotingAction(),
    "get_rounds": GetRoundsAction(),
    "request_brief": RequestBriefAction(),
    "voting_status": VotingStatusAction(),
    "vote": VoteAction(),
    # Web actions
    "web_search": WebSearchAction(),
    "view_page": ViewPageAction(),
}

SCENE_MAP = {
    "simple_chat_scene": SimpleChatScene,
    "council_scene": CouncilScene,
    "village_scene": VillageScene,
}
