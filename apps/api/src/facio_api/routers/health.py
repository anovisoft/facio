from typing import Annotated

from fastapi import APIRouter, Depends

from facio_api.config import Settings, UnknownModelError, get_settings

router = APIRouter(prefix="/v1", tags=["health"])

SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/health")
def health(settings: SettingsDep) -> dict[str, str | bool]:
    try:
        family: str = settings.family
        model = settings.resolved_model
    except UnknownModelError:
        family = "unknown"
        model = settings.model_name
    return {"ok": True, "mode": settings.talk_mode, "model": model, "provider": family}
