from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from facio_api.config import Settings, get_settings
from facio_api.providers.factory import provider_for
from facio_api.providers.types import LiveProviderError
from facio_api.talk.loop import TalkError, run_turn
from facio_api.talk.schemas import TalkTurnRequest, TalkTurnResponse

router = APIRouter(prefix="/v1", tags=["talk"])

SettingsDep = Annotated[Settings, Depends(get_settings)]


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
