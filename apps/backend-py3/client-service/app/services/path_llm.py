"""LLM prompt builders and PathState parsing."""

from __future__ import annotations

import json
from typing import Any

from app.schemas.path_state import PATH_RESPONSE_SCHEMA, PathState

__all__ = [
    "PATH_RESPONSE_SCHEMA",
    "messages_for_create",
    "messages_for_refine",
    "messages_for_repair",
    "parse_path_state",
]


def messages_for_create(intent: str) -> list[dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": (
                "Create a structured Path for the user's intent. "
                "Every action must include a non-empty why. "
                "Assign stable string ids to groups and actions. "
                "Respond with JSON matching the provided schema."
            ),
        },
        {"role": "user", "content": intent},
    ]


def messages_for_refine(
    *,
    current_state: dict[str, Any],
    answer: str,
    question_id: str | None,
) -> list[dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": (
                "Refine the Path using the user's clarification. "
                "Keep why non-empty on every action. "
                "Preserve action ids when the step is the same. "
                "Respond with JSON matching the provided schema."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "current_state": current_state,
                    "question_id": question_id,
                    "answer": answer,
                },
                ensure_ascii=False,
            ),
        },
    ]


def messages_for_repair(
    *,
    current_state: dict[str, Any],
    reason: str,
    project_status: str,
) -> list[dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": (
                "Repair / recompute the Path for the given reason. "
                "Preserve completed progress where possible by keeping "
                "the same action ids. "
                "Every action must include a non-empty why."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "current_state": current_state,
                    "reason": reason,
                    "project_status": project_status,
                },
                ensure_ascii=False,
            ),
        },
    ]


def parse_path_state(raw_response: Any) -> PathState:
    if isinstance(raw_response, PathState):
        return raw_response
    if isinstance(raw_response, str):
        data = json.loads(raw_response)
    elif isinstance(raw_response, dict):
        data = raw_response
    else:
        raise TypeError(
            f"Unexpected raw_response type: {type(raw_response)!r}"
        )
    return PathState.model_validate(data)
