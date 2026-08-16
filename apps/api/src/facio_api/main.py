from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException

from facio_api.config import Settings, get_settings
from facio_api.provider import provider_for
from facio_api.schemas import TalkTurnRequest, TalkTurnResponse
from facio_api.turn import TalkError, run_turn

app = FastAPI(title="Facio talk")
router = APIRouter(prefix="/v1", tags=["talk"])

SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/health")
def health(settings: SettingsDep) -> dict[str, str | bool]:
    return {"ok": True, "mode": settings.talk_mode}


@router.post("/talk/turn")
async def talk_turn(body: TalkTurnRequest, settings: SettingsDep) -> TalkTurnResponse:
    if settings.talk_mode == "live" and not settings.model_api_key:
        raise HTTPException(status_code=503, detail="model key missing")
    provider = provider_for(settings, body.utterance)
    try:
        return await run_turn(body, provider)
    except TalkError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error


app.include_router(router)
