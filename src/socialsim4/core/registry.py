from .actions.base_actions import SendMessageAction, TalkToAction, YieldAction, SpeakAction
from .actions.council_actions import (
    FinishMeetingAction,
    RequestBriefAction,
    StartVotingAction,
    VoteAction,
    VotingStatusAction,
)
from .actions.landlord_actions import (
    CallLandlordAction,
    DoubleAction,
    NoDoubleAction,
    PassAction,
    PlayCardsAction,
    RobLandlordAction,
)
from .actions.moderation_actions import ScheduleOrderAction
from .actions.village_actions import (
    # ExploreAction,
    GatherResourceAction,
    LookAroundAction,
    MoveToLocationAction,
    # QuickMoveAction,
    RestAction,
)
from .actions.web_actions import ViewPageAction, WebSearchAction
from .actions.werewolf_actions import (
    CloseVotingAction,
    InspectAction,
    NightKillAction,
    OpenVotingAction,
    VoteLynchAction,
    WitchPoisonAction,
    WitchSaveAction,
)
from .ordering import ORDERING_MAP as _ORDERING_MAP
from .scenes.council_scene import CouncilScene
from .scenes.landlord_scene import LandlordPokerScene
from .scenes.simple_chat_scene import SimpleChatScene
from .scenes.village_scene import VillageScene
from .scenes.werewolf_scene import WerewolfScene

ACTION_SPACE_MAP = {
    "speak": SpeakAction(),
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
    "finish_meeting": FinishMeetingAction(),
    "request_brief": RequestBriefAction(),
    "voting_status": VotingStatusAction(),
    "vote": VoteAction(),
    # Web actions
    "web_search": WebSearchAction(),
    "view_page": ViewPageAction(),
    # Moderation actions
    "schedule_order": ScheduleOrderAction(),
    # Werewolf actions
    "vote_lynch": VoteLynchAction(),
    "night_kill": NightKillAction(),
    "inspect": InspectAction(),
    "witch_save": WitchSaveAction(),
    "witch_poison": WitchPoisonAction(),
    # Moderator actions
    "open_voting": OpenVotingAction(),
    "close_voting": CloseVotingAction(),
    # Landlord poker actions
    "call_landlord": CallLandlordAction(),
    "rob_landlord": RobLandlordAction(),
    "pass": PassAction(),
    "play_cards": PlayCardsAction(),
    "double": DoubleAction(),
    "no_double": NoDoubleAction(),
}

SCENE_MAP = {
    "simple_chat_scene": SimpleChatScene,
    "council_scene": CouncilScene,
    "village_scene": VillageScene,
    "werewolf_scene": WerewolfScene,
    "landlord_scene": LandlordPokerScene,
}

ORDERING_MAP = _ORDERING_MAP
