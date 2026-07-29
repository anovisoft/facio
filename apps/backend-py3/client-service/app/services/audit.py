"""
Audit / product events.

Stored ``events.type`` values ↔ docs/mvp/04-metrics.md funnel names:

| Stored (server)           | Metrics doc          |
|---------------------------|----------------------|
| intent_submitted          | intent_submitted     |
| draft_created             | draft_shown          |
| plan_failed               | plan_failed          |
| refine_submitted          | refine_answered      |
| state_restored            | back_navigated       |
| project_committed         | committed            |
| action_completed          | action_done          |
| action_skipped            | action_skipped       |
| first_completion          | first_completion     |
| repair_requested          | repair_applied*      |
| checklist_item_toggled    | (not in funnel list) |
| project_completed         | (derived)            |

Client beacons via POST /events use metric names directly
(app_opened, path_opened, accept_viewed, action_shown, …).

*repair_requested is emitted on request; repair_applied once LLM succeeds.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ConversationRole,
    ConversationTurn,
    Event,
    LlmCall,
    StateSource,
    StateVersion,
)

# Soft allowlist for client POST /events (04-metrics + a few UI beacons).
CLIENT_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "app_opened",
        "soft_start_shown",
        "draft_shown",
        "accept_viewed",
        "action_shown",
        "path_opened",
        "project_switched",
        "back_navigated",
        "intent_submitted",
        "committed",
        "action_done",
        "action_skipped",
        "first_completion",
        "refine_answered",
        "plan_failed",
        "repair_applied",
    }
)


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add_turn(
        self,
        *,
        role: ConversationRole,
        content: str,
        project_id: UUID | None = None,
        meta: dict[str, Any] | None = None,
    ) -> ConversationTurn:
        turn = ConversationTurn(
            project_id=project_id,
            role=role,
            content=content,
            meta=meta,
        )
        self.db.add(turn)
        await self.db.flush()
        return turn

    async def add_llm_call(
        self,
        *,
        purpose: str,
        prompt_messages: list[dict[str, Any]] | dict[str, Any],
        project_id: UUID | None = None,
        model: str | None = None,
        raw_response: Any = None,
        parsed_ok: bool = False,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        latency_ms: int | None = None,
        error: str | None = None,
    ) -> LlmCall:
        call = LlmCall(
            project_id=project_id,
            purpose=purpose,
            model=model,
            prompt_messages=prompt_messages,
            raw_response=raw_response,
            parsed_ok=parsed_ok,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            error=error,
        )
        self.db.add(call)
        await self.db.flush()
        return call

    async def add_state_version(
        self,
        *,
        project_id: UUID,
        version: int,
        state_json: dict[str, Any],
        source: StateSource,
    ) -> StateVersion:
        row = StateVersion(
            project_id=project_id,
            version=version,
            state_json=state_json,
            source=source,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def add_event(
        self,
        *,
        event_type: str,
        user_id: UUID | None = None,
        project_id: UUID | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Event:
        event = Event(
            type=event_type,
            user_id=user_id,
            project_id=project_id,
            payload=payload,
        )
        self.db.add(event)
        await self.db.flush()
        return event
