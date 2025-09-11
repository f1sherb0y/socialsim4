from .actions.base_actions import SendMessageAction, SkipReplyAction
from .actions.map_actions import (
    ExploreAction,
    GatherResourceAction,
    LookAroundAction,
    MoveToLocationAction,
    QuickMoveAction,
    RestAction,
)
from .scenes.map_scene import MapScene
from .scenes.simple_chat_scene import SimpleChatScene
from .scenes.council_scene import CouncilScene
from .scenes.village_scene import VillageScene

ACTION_SPACE_MAP = {
    "send_message": SendMessageAction(),
    "skip_reply": SkipReplyAction(),
    "move_to_location": MoveToLocationAction(),
    "look_around": LookAroundAction(),
    "gather_resource": GatherResourceAction(),
    "rest": RestAction(),
    "quick_move": QuickMoveAction(),
    "explore": ExploreAction(),
}

SCENE_MAP = {
    "map_scene": MapScene,
    "simple_chat_scene": SimpleChatScene,
    "council_scene": CouncilScene,
    "village_scene": VillageScene,
}
