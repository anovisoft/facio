"""One talk turn: policy → model with tools → validated patch."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from facio_domain.models import CueOrigin, Desk
from facio_domain.pain import reports_pain
from facio_domain.tools import apply_tool, snapshot_cards

from facio_api.providers.types import ModelProvider, ModelTurn
from facio_api.talk.schemas import SnapshotCard, TalkTurnRequest, TalkTurnResponse, ToolCallRecord
from facio_api.talk.spec import SYSTEM_PROMPT, tool_schemas

MAX_ROUNDS = 8
MAX_UTTERANCE = 4000


class TalkError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


async def run_turn(
    body: TalkTurnRequest,
    provider: ModelProvider,
    *,
    now: datetime | None = None,
) -> TalkTurnResponse:
    utterance = body.utterance.strip()
    if not utterance:
        raise TalkError(422, "utterance required")
    if len(utterance) > MAX_UTTERANCE:
        raise TalkError(422, "utterance too long")
    stamp = now or body.now or datetime.now()
    pain = reports_pain(utterance)
    desk = body.desk.model_copy(deep=True)
    origin = CueOrigin(chat_id=body.thread_id, message_id=None)
    messages = _messages(body, utterance, pain)
    records: list[ToolCallRecord] = []
    mutated = False
    snapshot_ids: list[str] = []
    text = ""
    tools = tool_schemas()

    for _ in range(MAX_ROUNDS):
        turn = await provider.complete(messages, tools)
        if turn.tool_calls:
            messages.append(_assistant_tools(turn))
            for call in turn.tool_calls:
                outcome = apply_tool(
                    desk,
                    call.name,
                    call.arguments,
                    pain=pain,
                    now=stamp,
                    origin=origin,
                )
                desk = outcome.desk
                records.append(
                    ToolCallRecord(
                        name=call.name,
                        arguments=call.arguments,
                        ok=outcome.ok,
                        error=outcome.error,
                    )
                )
                if outcome.mutated:
                    mutated = True
                    snapshot_ids.extend(outcome.snapshot_widget_ids)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(
                            {
                                "ok": outcome.ok,
                                "error": outcome.error,
                                "data": outcome.data,
                            },
                            ensure_ascii=False,
                            default=str,
                        ),
                    }
                )
            continue
        text = (turn.text or "").strip()
        break

    if not text:
        text = "Готово." if mutated else "Могу объяснить или записать на стол — напиши ещё раз."
    cards = [SnapshotCard.model_validate(row) for row in snapshot_cards(desk, snapshot_ids)] if mutated else []
    return TalkTurnResponse(
        text=text,
        desk=desk,
        mutated=mutated,
        snapshots=cards,
        tool_calls=records,
        thread_id=body.thread_id,
    )


def _messages(body: TalkTurnRequest, utterance: str, pain: bool) -> list[dict[str, Any]]:
    desk_brief = json.dumps(
        {
            "subjects": [
                {
                    "id": subject.id,
                    "title": subject.title,
                    "cadence": subject.cadence.model_dump(mode="json"),
                    "target": subject.target.model_dump() if subject.target else None,
                    "status": subject.status,
                }
                for subject in body.desk.subjects
            ],
            "widgets": [
                {
                    "id": widget.id,
                    "type": widget.type,
                    "title": widget.title,
                    "section": widget.section,
                    "subject_id": widget.subject_id,
                }
                for widget in body.desk.widgets
            ],
            "focused_widget_id": body.focused_widget_id,
            "pain": pain,
        },
        ensure_ascii=False,
        default=str,
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Стол сейчас:\n{desk_brief}"},
    ]
    for row in body.thread[-20:]:
        role = row.role if row.role in {"user", "assistant"} else "user"
        messages.append({"role": role, "content": row.text})
    messages.append({"role": "user", "content": utterance})
    return messages


def _assistant_tools(turn: ModelTurn) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": turn.text or None,
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.name,
                    "arguments": json.dumps(call.arguments, ensure_ascii=False),
                },
            }
            for call in turn.tool_calls
        ],
    }
