"""Pain is a boundary. Detected in the utterance, not hoped for in a prompt."""

from __future__ import annotations

_NEEDLES = (
    "боль",
    "болит",
    "больно",
    "hurts",
    "hurt",
    "pain",
    "травм",
    "поясниц",
)


def reports_pain(utterance: str) -> bool:
    """True when the turn names pain, injury, or load in the lower back."""
    text = utterance.casefold()
    return any(needle in text for needle in _NEEDLES)
