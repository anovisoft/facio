from __future__ import annotations

from uuid import UUID

from app.models import Action, ActionGroup, ActionStatus, Project, ProjectStatus
from app.schemas.api import (
    ActionResponse,
    ChecklistItemResponse,
    CounterResponse,
    CurrentDayResponse,
    CycleResponse,
    DayResponse,
    GroupResponse,
    TimerResponse,
)
from app.schemas.path_state import DayKind, PathCounter, PathState, PathTimer
from app.services.path_materialize import action_key, stable_uuid


def _serialize_timers_from_orm(raw: list | None) -> list[TimerResponse]:
    if not raw:
        return []
    out: list[TimerResponse] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append(
            TimerResponse(
                id=str(item.get("id") or ""),
                title=str(item.get("title") or ""),
                duration_sec=int(item.get("duration_sec") or 0),
                signal=item.get("signal") or "nudge",  # type: ignore[arg-type]
                parallel_group=item.get("parallel_group"),
                completed=bool(item.get("completed", False)),
            )
        )
    return out


def _serialize_counter_from_orm(raw: dict | None) -> CounterResponse | None:
    if not isinstance(raw, dict):
        return None
    target = raw.get("target")
    if target is None or int(target) < 1:
        return None
    return CounterResponse(
        label=raw.get("label"),
        target=int(target),
        current=max(0, int(raw.get("current") or 0)),
        step=max(1, int(raw.get("step") or 1)),
    )


def _serialize_timers_from_state(
    timers: list[PathTimer],
) -> list[TimerResponse]:
    out: list[TimerResponse] = []
    for t_index, timer in enumerate(timers):
        t_key = timer.id or f"t{t_index}"
        out.append(
            TimerResponse(
                id=t_key,
                title=timer.title,
                duration_sec=timer.duration_sec,
                signal=timer.signal,
                parallel_group=timer.parallel_group,
                completed=False,
            )
        )
    return out


def _serialize_counter_from_state(
    counter: PathCounter | None,
) -> CounterResponse | None:
    if counter is None:
        return None
    return CounterResponse(
        label=counter.label,
        target=counter.target,
        current=counter.current,
        step=counter.step,
    )


def serialize_action(action: Action) -> ActionResponse:
    group = action.group
    return ActionResponse(
        id=action.id,
        project_id=action.project_id,
        key=action.key,
        title=action.title,
        why=action.why,
        detail=action.detail,
        estimate_min=action.estimate_min,
        due_at=action.due_at,
        sort=action.sort,
        status=action.status.value,
        day_offset=action.day_offset,
        group_id=action.group_id,
        group_key=group.key if group else None,
        group_title=group.title if group else None,
        checklist_items=[
            ChecklistItemResponse.model_validate(item, from_attributes=True)
            for item in sorted(action.checklist_items, key=lambda i: i.sort)
        ],
        timers=_serialize_timers_from_orm(action.timers),
        counter=_serialize_counter_from_orm(action.counter),
    )


def serialize_groups(groups: list[ActionGroup]) -> list[GroupResponse]:
    return [
        GroupResponse.model_validate(g, from_attributes=True)
        for g in sorted(groups, key=lambda g: g.sort)
    ]


def serialize_cycle_from_state(state: PathState) -> CycleResponse:
    return CycleResponse(
        index=state.cycle.index,
        horizon_days=state.cycle.horizon_days,
        status=state.cycle.status,
        goal_for_cycle=state.cycle.goal_for_cycle,
    )


def serialize_cycle_from_project(project: Project) -> CycleResponse | None:
    if project.cycle_horizon_days is None:
        return None
    return CycleResponse(
        index=project.cycle_index or 1,
        horizon_days=project.cycle_horizon_days,
        status=project.cycle_status or "draft",
        goal_for_cycle=project.cycle_goal,
    )


def serialize_days_from_state(state: PathState) -> list[DayResponse]:
    return [
        DayResponse(
            day_index=day.day_index,
            kind=day.kind,
            title=day.title,
            summary=day.summary,
        )
        for day in sorted(state.days, key=lambda d: d.day_index)
    ]


def serialize_days_from_project(project: Project) -> list[DayResponse]:
    raw = project.schedule_days or []
    days: list[DayResponse] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        days.append(
            DayResponse(
                day_index=int(item["day_index"]),
                kind=item["kind"],  # type: ignore[arg-type]
                title=item.get("title"),
                summary=item.get("summary"),
            )
        )
    return sorted(days, key=lambda d: d.day_index)


def _day_by_index(days: list[DayResponse]) -> dict[int, DayResponse]:
    return {d.day_index: d for d in days}


def resolve_current_day(
    *,
    cycle: CycleResponse | None,
    days: list[DayResponse],
    next_action: ActionResponse | None,
    actions: list[ActionResponse] | None = None,
) -> CurrentDayResponse | None:
    """Pick the cycle day for Home from next focus action (schedule-aware)."""
    if cycle is None:
        return None
    day_map = _day_by_index(days)
    day_index: int | None = None
    if next_action is not None and next_action.day_offset is not None:
        day_index = next_action.day_offset
    elif actions:
        pending = [
            a
            for a in actions
            if a.status == ActionStatus.pending.value
            and a.day_offset is not None
        ]
        if pending:
            day_index = min(a.day_offset for a in pending if a.day_offset is not None)
    if day_index is None:
        day_index = 0 if days else None
    if day_index is None:
        return CurrentDayResponse(
            day_index=0,
            day_number=1,
            horizon_days=cycle.horizon_days,
            kind="other",
            title=None,
            summary=None,
        )
    day = day_map.get(day_index)
    kind: DayKind = day.kind if day else "other"
    return CurrentDayResponse(
        day_index=day_index,
        day_number=day_index + 1,
        horizon_days=cycle.horizon_days,
        kind=kind,
        title=day.title if day else None,
        summary=day.summary if day else None,
    )


def serialize_path_state(
    project: Project, state: PathState
) -> tuple[list[GroupResponse], list[ActionResponse]]:
    """Serialize draft PathState into API shapes with stable uuid5 ids."""
    group_by_key = {g.id: g for g in state.groups}
    groups = [
        GroupResponse(
            id=stable_uuid(project.id, "group", g.id),
            key=g.id,
            title=g.title,
            description=g.description,
            sort=g.sort,
        )
        for g in sorted(state.groups, key=lambda g: g.sort)
    ]
    actions: list[ActionResponse] = []
    for index, item in enumerate(state.actions):
        key = action_key(item, index)
        action_id = stable_uuid(project.id, "action", key)
        group_key = item.group_id
        group_spec = group_by_key.get(group_key) if group_key else None
        sort = item.sort if item.sort is not None else index
        checklist = []
        for c_index, c in enumerate(item.checklist_items):
            c_key = c.id or f"c{c_index}"
            checklist.append(
                ChecklistItemResponse(
                    id=stable_uuid(project.id, "checklist", f"{key}:{c_key}"),
                    action_id=action_id,
                    key=c_key,
                    title=c.title,
                    done=c.done,
                    sort=c.sort if c.sort is not None else c_index,
                )
            )
        actions.append(
            ActionResponse(
                id=action_id,
                project_id=project.id,
                key=key,
                title=item.title,
                why=item.why,
                detail=item.detail,
                estimate_min=item.estimate_min,
                due_at=None,
                sort=sort,
                status=ActionStatus.pending.value,
                day_offset=item.day_offset,
                group_id=(
                    stable_uuid(project.id, "group", group_key)
                    if group_key
                    else None
                ),
                group_key=group_key,
                group_title=group_spec.title if group_spec else None,
                checklist_items=checklist,
                timers=_serialize_timers_from_state(item.timers),
                counter=_serialize_counter_from_state(item.counter),
            )
        )
    actions.sort(
        key=lambda a: (
            a.day_offset if a.day_offset is not None else 10**9,
            next((g.sort for g in groups if g.key == a.group_key), 10**9),
            a.sort,
        )
    )
    return groups, actions


def action_queue_key(action: Action) -> tuple[int, int, int]:
    """Order: day_offset, group.sort (ungrouped last), then action.sort."""
    day = action.day_offset if action.day_offset is not None else 10**9
    group_sort = action.group.sort if action.group is not None else 10**9
    return (day, group_sort, action.sort)


def pick_next_action(project: Project) -> Action | None:
    """First pending action for an active project (day → group → sort)."""
    if project.status != ProjectStatus.active:
        return None
    pending = [a for a in project.actions if a.status == ActionStatus.pending]
    if not pending:
        return None
    return sorted(pending, key=action_queue_key)[0]
