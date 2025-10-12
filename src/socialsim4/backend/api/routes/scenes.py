from fastapi import APIRouter

from socialsim4.core.registry import SCENE_MAP


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

    if scene_key == "simple_chat_scene":
        config_schema = {
            "initial_news": config_schema.get("initial_news") or DEFAULT_SIMPLE_CHAT_NEWS,
        }
    elif scene_key == "council_scene":
        config_schema = {
            "draft_text": config_schema.get("draft_text") or DEFAULT_COUNCIL_DRAFT,
        }

    return {
        "type": scene_cls.TYPE,
        "name": scene_cls.__name__,
        "config_schema": config_schema,
    }


@router.get("/")
async def list_scenes() -> list[dict]:
    scenes: list[dict] = []
    for key, cls in SCENE_MAP.items():
        if key not in PUBLIC_SCENE_KEYS:
            continue
        try:
            scenes.append(scene_config_template(key, cls))
        except TypeError:
            # Scene requires additional constructor args; skip exposing for now.
            continue
    return scenes
