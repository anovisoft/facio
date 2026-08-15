from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from facio_api.llm import AnthropicTurnGenerator, TurnGenerator
from facio_api.patches import PatchRejected, TurnOut
from facio_api.settings import Settings, load_settings
from facio_api.turns import TurnIn, run_turn

app = FastAPI(title="Facio talk", version="0.0.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_settings() -> Settings:
    return load_settings()


def get_llm(settings: Settings = Depends(get_settings)) -> TurnGenerator:
    if not settings.anthropic_api_key.strip():
        raise HTTPException(status_code=501, detail="ANTHROPIC_API_KEY is not set")
    return AnthropicTurnGenerator(
        api_key=settings.anthropic_api_key,
        model=settings.anthropic_model,
    )


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/v1/turns", response_model=TurnOut)
async def create_turn(body: TurnIn, llm: TurnGenerator = Depends(get_llm)) -> TurnOut:
    try:
        return await run_turn(body, llm)
    except PatchRejected as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
