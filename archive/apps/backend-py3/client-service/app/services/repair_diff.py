"""Human-readable before → after Diff for Repair preview (Facio 0.1 §11.5)."""

from __future__ import annotations

from app.schemas.path_state import PathAction, PathDay, PathState


def _day_label(day: PathDay | None, day_index: int) -> str:
    n = day_index + 1
    if day is None:
        return f"Day {n}"
    title = (day.title or "").strip()
    kind = (day.kind or "").strip()
    if title:
        return f"Day {n} · {title}"
    if kind and kind not in {"other", "cook_session"}:
        return f"Day {n} · {kind}"
    return f"Day {n}"


def _action_key(action: PathAction, index: int) -> str:
    return (action.id or "").strip() or f"a{index}"


def _action_has_filled_plugins(action: PathAction) -> bool:
    return bool(
        action.timers
        or action.counter is not None
        or action.timeline is not None
        or action.interval_plan is not None
        or action.stepper is not None
    )


def _plugins_awaiting_rematerialize(
    before: PathState, after: PathState
) -> bool:
    """True when a prior filled tool was stripped (lighten/rest rematerialize)."""
    before_actions = {
        _action_key(a, i): a for i, a in enumerate(before.actions)
    }
    after_actions = {
        _action_key(a, i): a for i, a in enumerate(after.actions)
    }
    for key in set(before_actions) & set(after_actions):
        ba = before_actions[key]
        aa = after_actions[key]
        if not _action_has_filled_plugins(ba):
            continue
        if _action_has_filled_plugins(aa):
            continue
        hints = list(aa.plugin_hints or ba.plugin_hints or [])
        if hints:
            return True
    return False


def build_repair_diff(before: PathState, after: PathState) -> list[dict[str, str]]:
    """Return ``[{before, after}, ...]`` lines for the Repair confirm UI.

    Prefer concrete Session/day mutations over paraphrase. Falls back to a
    single summary line when structure is unchanged but text moved.
    """
    lines: list[dict[str, str]] = []

    bh = before.cycle.horizon_days
    ah = after.cycle.horizon_days
    if bh != ah:
        lines.append({"before": f"{bh} days", "after": f"{ah} days"})

    before_days = {d.day_index: d for d in before.days}
    after_days = {d.day_index: d for d in after.days}
    for idx in sorted(set(before_days) | set(after_days)):
        bl = _day_label(before_days.get(idx), idx)
        al = _day_label(after_days.get(idx), idx)
        if bl != al:
            lines.append({"before": bl, "after": al})

    before_actions = {
        _action_key(a, i): a for i, a in enumerate(before.actions)
    }
    after_actions = {
        _action_key(a, i): a for i, a in enumerate(after.actions)
    }

    for key in sorted(set(before_actions) & set(after_actions)):
        ba = before_actions[key]
        aa = after_actions[key]
        if ba.day_offset != aa.day_offset:
            b_day = (ba.day_offset if ba.day_offset is not None else 0) + 1
            a_day = (aa.day_offset if aa.day_offset is not None else 0) + 1
            lines.append(
                {"before": f"Day {b_day}", "after": f"Day {a_day}"}
            )
        if ba.title.strip() != aa.title.strip():
            lines.append({"before": ba.title.strip(), "after": aa.title.strip()})

    for key in sorted(set(after_actions) - set(before_actions)):
        aa = after_actions[key]
        lines.append({"before": "—", "after": aa.title.strip()})

    for key in sorted(set(before_actions) - set(after_actions)):
        ba = before_actions[key]
        lines.append({"before": ba.title.strip(), "after": "—"})

    if _plugins_awaiting_rematerialize(before, after):
        lines.append(
            {
                "before": "Previous load (sets)",
                "after": "Lighter load (tool updates)",
            }
        )

    if lines:
        # Deduplicate while preserving order (day_offset + day row can twin).
        seen: set[tuple[str, str]] = set()
        unique: list[dict[str, str]] = []
        for line in lines:
            pair = (line["before"], line["after"])
            if pair in seen or line["before"] == line["after"]:
                continue
            seen.add(pair)
            unique.append(line)
        if unique:
            return unique[:12]

    b_sum = (before.summary or before.paraphrase or before.title or "").strip()
    a_sum = (after.summary or after.paraphrase or after.title or "").strip()
    if b_sum != a_sum and a_sum:
        return [
            {
                "before": b_sum[:120] or "—",
                "after": a_sum[:120],
            }
        ]

    return [{"before": "Current plan", "after": after.paraphrase.strip() or "Updated plan"}]
