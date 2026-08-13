"""Cycle finish / archive helpers for next-cycle (Slice 5).

See docs/next/04-model.md §7 and docs/next/05 «Конец цикла → следующий».
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.models import Action, ActionStatus, Project
from app.schemas.api import (
    ContinueKind,
    CycleHistoryEntry,
    CycleResultResponse,
)


def continue_kind_for_project(project: Project) -> ContinueKind:
    """Cook / single-day → «Повторить»; multi-day → «Следующий цикл»."""
    horizon = project.cycle_horizon_days or 1
    if horizon <= 1 or (project.domain or "") == "cooking":
        return "repeat"
    return "next"


def build_cycle_result(
    project: Project,
    *,
    partial: bool = False,
    partial_notes: str | None = None,
    user_comment: str | None = None,
    finished_at: datetime | None = None,
) -> CycleResultResponse:
    """Build structured cycle_result from current ORM actions."""
    completed = 0
    skipped = 0
    pending = 0
    counters: list[dict[str, Any]] = []
    for action in project.actions:
        if action.status == ActionStatus.done:
            completed += 1
        elif action.status == ActionStatus.skipped:
            skipped += 1
        else:
            pending += 1
        snap = _counter_snapshot(action)
        if snap is not None:
            counters.append(snap)
    return CycleResultResponse(
        completed_steps=completed,
        skipped_steps=skipped,
        pending_steps=pending,
        partial=partial or pending > 0,
        partial_notes=(partial_notes or "").strip() or None,
        counters_snapshot=counters,
        user_comment=(user_comment or "").strip() or None,
        finished_at=finished_at or datetime.now(UTC),
    )


def _counter_snapshot(action: Action) -> dict[str, Any] | None:
    """Capture dose facts (action counter + stepper work/measure currents)."""
    out: dict[str, Any] = {
        "action_key": action.key,
        "title": action.title,
    }
    has = False
    if isinstance(action.counter, dict) and "current" in action.counter:
        out["counter"] = {
            "label": action.counter.get("label"),
            "target": action.counter.get("target"),
            "current": action.counter.get("current"),
        }
        has = True
    beats: list[dict[str, Any]] = []
    if isinstance(action.stepper, dict):
        for beat in action.stepper.get("beats") or []:
            if not isinstance(beat, dict):
                continue
            counter = beat.get("counter")
            if not isinstance(counter, dict) or "current" not in counter:
                continue
            beats.append(
                {
                    "id": beat.get("id"),
                    "kind": beat.get("kind"),
                    "title": beat.get("title"),
                    "current": counter.get("current"),
                    "target": counter.get("target"),
                }
            )
    if beats:
        out["stepper_beats"] = beats
        has = True
    return out if has else None


def lean_path_snapshot(state_json: dict[str, Any] | None) -> dict[str, Any] | None:
    """Enough of the prior Path for history UI / next-cycle prompt context."""
    if not isinstance(state_json, dict):
        return None
    actions_out: list[dict[str, Any]] = []
    for action in state_json.get("actions") or []:
        if not isinstance(action, dict):
            continue
        actions_out.append(
            {
                "id": action.get("id"),
                "title": action.get("title"),
                "day_offset": action.get("day_offset"),
                "status": action.get("status"),
                "plugin_hints": list(action.get("plugin_hints") or []),
            }
        )
    days_out: list[dict[str, Any]] = []
    for day in state_json.get("days") or []:
        if not isinstance(day, dict):
            continue
        days_out.append(
            {
                "day_index": day.get("day_index"),
                "kind": day.get("kind"),
                "title": day.get("title"),
                "summary": day.get("summary"),
            }
        )
    cycle = state_json.get("cycle") if isinstance(state_json.get("cycle"), dict) else {}
    return {
        "title": state_json.get("title"),
        "summary": state_json.get("summary"),
        "outcome": state_json.get("outcome"),
        "domain": state_json.get("domain"),
        "cycle": {
            "index": cycle.get("index"),
            "horizon_days": cycle.get("horizon_days"),
            "goal_for_cycle": cycle.get("goal_for_cycle"),
        },
        "days": days_out,
        "actions": actions_out,
    }


def archive_cycle_entry(
    project: Project,
    *,
    cycle_result: CycleResultResponse,
    path_snapshot: dict[str, Any] | None,
) -> CycleHistoryEntry:
    return CycleHistoryEntry(
        index=int(project.cycle_index or 1),
        horizon_days=int(project.cycle_horizon_days or 1),
        goal_for_cycle=project.cycle_goal,
        title=project.title,
        summary=project.summary,
        cycle_result=cycle_result,
        path_snapshot=path_snapshot,
        completed_at=cycle_result.finished_at,
    )


def parse_cycle_result(raw: dict | None) -> CycleResultResponse | None:
    if not isinstance(raw, dict):
        return None
    return CycleResultResponse.model_validate(raw)


def parse_cycles_history(raw: list | None) -> list[CycleHistoryEntry]:
    if not isinstance(raw, list):
        return []
    out: list[CycleHistoryEntry] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(CycleHistoryEntry.model_validate(item))
    return out


def cycle_cta_flags(
    project: Project,
) -> tuple[bool, bool, ContinueKind | None]:
    """Return (next_cycle_available, can_finish_cycle, continue_kind)."""
    cycle_status = (project.cycle_status or "").lower()
    cycle_done = cycle_status == "completed" or (
        project.status.value == "completed" and project.cycle_result is not None
    )
    if cycle_done:
        return True, False, continue_kind_for_project(project)

    if project.status.value != "active":
        return False, False, None

    actions = list(project.actions)
    if not actions:
        return False, False, None
    done_or_skipped = sum(
        1
        for a in actions
        if a.status in {ActionStatus.done, ActionStatus.skipped}
    )
    pending = sum(1 for a in actions if a.status == ActionStatus.pending)
    can_finish = done_or_skipped > 0 and pending > 0
    return False, can_finish, None
