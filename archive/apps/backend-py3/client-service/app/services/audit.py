"""Audit trail: conversation turns, LLM calls, state versions, product events.

Event type names match docs/mvp/04-metrics.md (single vocabulary for
server emitters and client beacons).
"""

from __future__ import annotations

import enum
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


class EventType(str, enum.Enum):
    # Shared / funnel
    app_opened = "app_opened"
    soft_start_shown = "soft_start_shown"
    intent_submitted = "intent_submitted"
    instant_answer_shown = "instant_answer_shown"
    draft_shown = "draft_shown"
    accept_viewed = "accept_viewed"
    action_shown = "action_shown"
    path_opened = "path_opened"
    project_switched = "project_switched"
    back_navigated = "back_navigated"
    refine_answered = "refine_answered"
    plan_failed = "plan_failed"
    committed = "committed"
    action_done = "action_done"
    action_skipped = "action_skipped"
    action_uncompleted = "action_uncompleted"
    first_completion = "first_completion"
    day_postponed = "day_postponed"
    repair_requested = "repair_requested"
    repair_applied = "repair_applied"
    manual_edit_applied = "manual_edit_applied"
    # Extra server-side (not all are client beacons)
    checklist_item_toggled = "checklist_item_toggled"
    counter_updated = "counter_updated"
    timer_completed = "timer_completed"
    project_completed = "project_completed"
    project_abandoned = "project_abandoned"
    cycle_completed = "cycle_completed"
    next_cycle_started = "next_cycle_started"


# UI beacons only — mutation facts (intent/commit/done/…) are server-emitted
# elsewhere. Overlap here double-counts funnel KPIs in docs/mvp/04-metrics.md.
CLIENT_EVENT_TYPES: frozenset[str] = frozenset(
    {
        EventType.app_opened.value,
        EventType.accept_viewed.value,
        EventType.action_shown.value,
        EventType.path_opened.value,
        EventType.project_switched.value,
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
        user_id: UUID | None = None,
        project_id: UUID | None = None,
        meta: dict[str, Any] | None = None,
    ) -> ConversationTurn:
        turn = ConversationTurn(
            user_id=user_id,
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
        user_id: UUID | None = None,
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
            user_id=user_id,
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
        event_type: EventType | str,
        user_id: UUID | None = None,
        project_id: UUID | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Event:
        type_value = (
            event_type.value if isinstance(event_type, EventType) else event_type
        )
        event = Event(
            type=type_value,
            user_id=user_id,
            project_id=project_id,
            payload=payload,
        )
        self.db.add(event)
        await self.db.flush()
        return event
