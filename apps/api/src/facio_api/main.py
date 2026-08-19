from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException

from facio_api.config import Settings, UnknownModelError, get_settings
from facio_api.provider import LiveProviderError, provider_for
from facio_api.schemas import TalkTurnRequest, TalkTurnResponse
from facio_api.turn import TalkError, run_turn

app = FastAPI(title="Facio talk")
router = APIRouter(prefix="/v1", tags=["talk"])

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


@router.post("/talk/turn")
async def talk_turn(body: TalkTurnRequest, settings: SettingsDep) -> TalkTurnResponse:
    try:
        provider = provider_for(settings, body.utterance)
    except LiveProviderError as error:
        raise HTTPException(status_code=503, detail=error.detail) from error
    try:
        return await run_turn(body, provider)
    except TalkError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error


app.include_router(router)
