from __future__ import annotations

from typing import Any

from facio_api.providers.types import ModelToolCall, ModelTurn
from facio_api.talk.goldens import Golden, match_golden


class ScriptedProvider:
    """Plays a golden. Unknown utterances stay text — no invented patch."""

    def __init__(self, golden: Golden | None) -> None:
        self._turns = list(golden.scripted) if golden else []
        self._index = 0

    @classmethod
    def for_utterance(cls, utterance: str) -> ScriptedProvider:
        return cls(match_golden(utterance))

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelTurn:
        del messages, tools
        if self._index >= len(self._turns):
            return ModelTurn(
                text="Скриптованный стенд знает только золотые реплики. Для живого рта нужен ключ модели на сервере."
            )
        step = self._turns[self._index]
        self._index += 1
        calls = [
            ModelToolCall(id=f"call_{self._index}_{offset}", name=call.name, arguments=call.arguments)
            for offset, call in enumerate(step.tool_calls)
        ]
        return ModelTurn(text=step.text, tool_calls=calls)
