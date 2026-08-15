"""Pain policy runs on the patch before it is returned. The prompt is not the gate."""

from __future__ import annotations

from typing import Never

from facio_domain.models import Cadence, Subject
from facio_domain.pain import reports_pain

from facio_api.patches import (
    AddCuePatch,
    NonePatch,
    Patch,
    PatchRejected,
    SetCadencePatch,
    SetTargetPatch,
    ShrinkPatch,
)

_PERIOD_RANK = {"none": 0, "week": 1, "day": 2}


def cadence_is_raise(proposed: Cadence, current: Cadence) -> bool:
    if _PERIOD_RANK[proposed.period] > _PERIOD_RANK[current.period]:
        return True
    if proposed.period == current.period and proposed.period != "none":
        return (proposed.count or 0) > (current.count or 0)
    return False


def target_is_raise(goal: int, subject: Subject) -> bool:
    if subject.target is None:
        return True
    return goal > subject.target.goal


def apply_pain_policy(utterance: str, subject: Subject, patches: list[Patch]) -> list[Patch]:
    """Drop target/cadence raises when the utterance reports pain.

    Remaining safe ops (add_cue, shrink, none, a non-raise set) are kept.
    Growth-only turns become 422 so the desk does not change.
    """
    if not reports_pain(utterance):
        return patches

    kept: list[Patch] = []
    dropped_growth = False
    for patch in patches:
        match patch:
            case AddCuePatch() | ShrinkPatch() | NonePatch():
                kept.append(patch)
            case SetTargetPatch():
                if target_is_raise(patch.goal, subject):
                    dropped_growth = True
                    continue
                kept.append(patch)
            case SetCadencePatch():
                proposed = Cadence.of(patch.count, patch.period)
                if cadence_is_raise(proposed, subject.cadence):
                    dropped_growth = True
                    continue
                kept.append(patch)
            case _:
                unreachable: Never = patch
                raise PatchRejected(str(unreachable))

    mutating = [item for item in kept if not isinstance(item, NonePatch)]
    if dropped_growth and not mutating:
        raise PatchRejected("pain: cannot raise target or cadence")
    return kept
