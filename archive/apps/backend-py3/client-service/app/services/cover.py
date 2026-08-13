"""Guide Cover heuristics (Facio 0.1 Slice B).

D7 prefers LLM emoji/difficulty/duration on create #1/#2, but expanding
Anthropic constrained schemas risks `400 grammar too large`. v0 fills Cover
from domain / title / horizon / action estimates after PathState is applied —
no grammar change.
"""

from __future__ import annotations

from app.models import Project
from app.schemas.path_state import PathState

DOMAIN_EMOJI: dict[str, str] = {
    "cooking": "🍝",
    "fitness": "🏋️",
    "learning": "📚",
    "home": "🏠",
    "errands": "🛒",
    "work": "💼",
    "health": "💚",
    "finance": "💰",
    "social": "👋",
    "other": "✨",
}


def _title_mark(title: str | None) -> str:
    raw = (title or "").strip()
    if not raw:
        return "✨"
    # Prefer first alphanumeric / letter; fall back to first char.
    for ch in raw:
        if ch.isalnum():
            return ch.upper()
    return raw[0]


def _difficulty(domain: str | None, horizon_days: int) -> str:
    if domain == "cooking" or horizon_days <= 1:
        return "Easy"
    if horizon_days <= 7:
        return "Medium"
    return "Hard"


def _duration_summary(state: PathState) -> str:
    horizon = (state.horizon or "").strip()
    if horizon and horizon not in {"…", "...", "—", "-"}:
        return horizon[:64]

    days = max(1, int(state.cycle.horizon_days or 1))
    if days > 1:
        return f"{days} days"

    estimates = [
        a.estimate_min
        for a in state.actions
        if a.estimate_min is not None and a.estimate_min > 0
    ]
    if estimates:
        total = sum(estimates)
        return f"{total} min"

    n = len(state.actions)
    if n > 0:
        return f"{n} sessions" if n != 1 else "1 session"

    return "1 session"


def apply_cover_fallback(project: Project, state: PathState) -> None:
    """Set Cover columns from PathState (always refresh on contract apply)."""
    domain = state.domain or project.domain or "other"
    emoji = DOMAIN_EMOJI.get(domain) or _title_mark(state.title or project.title)
    days = max(1, int(state.cycle.horizon_days or project.cycle_horizon_days or 1))
    project.cover_emoji = emoji[:16]
    project.cover_difficulty = _difficulty(domain, days)[:32]
    project.cover_duration_summary = _duration_summary(state)[:64]
