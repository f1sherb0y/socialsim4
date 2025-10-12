from fastapi import APIRouter

from socialsim4.core.registry import SCENE_MAP


router = APIRouter()


def scene_config_template(scene_cls) -> dict:
    scene = scene_cls("preview", "")
    return {
        "type": scene_cls.TYPE,
        "name": scene_cls.__name__,
        "config_schema": scene.serialize_config(),
    }


@router.get("/")
async def list_scenes() -> list[dict]:
    return [scene_config_template(cls) for cls in SCENE_MAP.values()]
