from fastapi import APIRouter

from socialsim4.core.agent import Agent
from socialsim4.core.registry import SCENE_ACTIONS, SCENE_DESCRIPTIONS, SCENE_MAP


router = APIRouter()

PUBLIC_SCENE_KEYS = {key for key in SCENE_MAP.keys()} - {"village_scene"}

DEFAULT_SIMPLE_CHAT_NEWS = (
    "News: A new study suggests AI models now match human-level performance in creative writing benchmarks."
)

DEFAULT_COUNCIL_DRAFT = (
    "Draft Ordinance: Urban Air Quality and Congestion Management (Pilot).\n"
    "1) Establish a 12-month congestion charge pilot in the CBD with base fee 30 CNY per entry.\n"
    "2) Revenue ring-fenced for transit upgrades and air-quality programs.\n"
    "3) Monthly public dashboard on PM2.5/NOx, traffic speed, ridership.\n"
    "4) Camera enforcement with strict privacy limits.\n"
    "5) Independent evaluation at 12 months with target reductions."
)


def scene_config_template(scene_key: str, scene_cls) -> dict:
    scene = scene_cls("preview", "")
    config_schema = scene.serialize_config() or {}

    if scene_key == "council_scene":
        config_schema = {
            "draft_text": config_schema.get("draft_text") or DEFAULT_COUNCIL_DRAFT,
        }
    # Generalized initial events list for all scenes (shown separately in UI)
    # Provide a friendly default for simple chat
    if scene_key == "simple_chat_scene":
        config_schema["initial_events"] = [DEFAULT_SIMPLE_CHAT_NEWS]
    else:
        config_schema.setdefault("initial_events", [])

    # Read from registry; fallback to scene introspection if not present
    reg = SCENE_ACTIONS.get(scene_key)
    if reg:
        basic_actions = list(reg.get("basic", []))
        allowed = set(reg.get("allowed", []))
    else:
        dummy = Agent.deserialize(
            {
                "name": "Preview",
                "user_profile": "",
                "style": "",
                "initial_instruction": "",
                "role_prompt": "",
                "action_space": [],
                "properties": {},
            }
        )
        basic_actions = [a.NAME for a in (scene.get_scene_actions(dummy) or []) if getattr(a, "NAME", None)]
        allowed = set()
    allowed_list = sorted(a for a in allowed if a not in set(basic_actions) and a != "yield")
    basic_list = sorted(a for a in basic_actions if a != "yield")

    return {
        "type": scene_cls.TYPE,
        "name": scene_cls.__name__,
        "description": SCENE_DESCRIPTIONS.get(scene_key) or scene.get_scenario_description() or "",
        "config_schema": config_schema,
        "allowed_actions": allowed_list,
        "basic_actions": basic_list,
    }


@router.get("/")
async def list_scenes() -> list[dict]:
    scenes: list[dict] = []
    for key, cls in SCENE_MAP.items():
        if key not in PUBLIC_SCENE_KEYS:
            continue
        scenes.append(scene_config_template(key, cls))
    return scenes
