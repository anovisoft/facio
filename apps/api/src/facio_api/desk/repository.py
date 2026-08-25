"""Load/merge/save a `Desk` for an account.

Q20: structure (widget shape, `version`) is last-write-wins; progress (a
running widget's live count/elapsed/etc.) merges per widget and a stale
structural write must never drop a newer progress value. This module owns
that merge — it is network conflict-resolution, not domain law, so it lives
here rather than in `packages/domain`; it only uses `Desk`/`Widget` as types.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from facio_domain.models import Desk

from facio_api.desk.models import DeskSnapshotRow

_PROGRESS_FIELDS = ("count", "done", "items", "seconds", "elapsed", "steps", "current")


def _split(desk: Desk) -> tuple[dict[str, Any], dict[str, Any]]:
    """Structure = the desk with progress fields stripped from each *running*
    widget's payload. Progress = {widget_id: {progress fields..., status:
    "running"}}, one entry per currently-running widget.

    Only a `running` widget's numbers are "live progress" in the Q20 sense —
    a resting widget's `count`/`target` etc. are ordinary structural state
    (e.g. a counter's baseline) and must follow structural LWW like the rest
    of its payload, or a stale structural write would look like it should
    "win" on progress too and clobber a genuinely newer running value.
    """
    dumped = desk.model_dump(mode="json")
    progress: dict[str, Any] = {}
    for widget in dumped["widgets"]:
        if widget.get("status") != "running":
            continue
        payload = dict(widget.get("payload") or {})
        entry = {field: payload[field] for field in _PROGRESS_FIELDS if payload.get(field) is not None}
        entry["status"] = "running"
        progress[widget["id"]] = entry
        for field in _PROGRESS_FIELDS:
            payload.pop(field, None)
        widget["payload"] = payload
    return dumped, progress


def _apply_progress(structure: dict[str, Any], progress: dict[str, Any]) -> dict[str, Any]:
    merged = {**structure, "widgets": [dict(widget) for widget in structure["widgets"]]}
    by_id = {widget["id"]: widget for widget in merged["widgets"]}
    for widget_id, entry in progress.items():
        widget = by_id.get(widget_id)
        if widget is None:
            continue
        entry = dict(entry)
        status = entry.pop("status", None)
        widget["payload"] = {**widget.get("payload", {}), **entry}
        if status == "running":
            widget["status"] = "running"
    return merged


def _merge_structures_and_progress(
    current_structure: dict[str, Any] | None,
    current_progress: dict[str, Any] | None,
    incoming_structure: dict[str, Any],
    incoming_progress: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if current_structure is None:
        return incoming_structure, incoming_progress

    current_by_id = {widget["id"]: widget for widget in current_structure.get("widgets", [])}
    merged_progress = dict(current_progress or {})
    merged_widgets = []
    for widget in incoming_structure["widgets"]:
        widget_id = widget["id"]
        prior = current_by_id.get(widget_id)
        if prior is None:
            incoming_wins = True
        else:
            prior_version = prior.get("version", 0)
            incoming_version = widget.get("version", 0)
            if incoming_version != prior_version:
                incoming_wins = incoming_version > prior_version
            else:
                # Same version: a running prior protects itself from a same-
                # version write that doesn't know about the run in progress.
                incoming_wins = prior.get("status") != "running"
        winner = widget if incoming_wins else prior
        merged_widgets.append(winner)

        if winner.get("status") == "running":
            # The winning write is a live one — take its progress entry if it
            # has one, else leave whatever was already stored for this widget.
            if incoming_wins and widget_id in incoming_progress:
                merged_progress[widget_id] = incoming_progress[widget_id]
        else:
            # The winning write is not running: any stored progress for this
            # widget is now stale (its own structural fields are current).
            merged_progress.pop(widget_id, None)
    return {**incoming_structure, "widgets": merged_widgets}, merged_progress


def merge(
    current_structure: dict[str, Any] | None,
    current_progress: dict[str, Any] | None,
    incoming: Desk,
) -> tuple[dict[str, Any], dict[str, Any], Desk]:
    """Pure merge, no I/O — kept separate from `DeskRepository` so it's testable
    without a database (see M4's structure-LWW / progress-survives tests)."""
    incoming_structure, incoming_progress = _split(incoming)
    merged_structure, merged_progress = _merge_structures_and_progress(
        current_structure, current_progress, incoming_structure, incoming_progress
    )
    merged_desk = Desk.model_validate(_apply_progress(merged_structure, merged_progress))
    return merged_structure, merged_progress, merged_desk


class DeskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load(self, account_id: UUID) -> Desk | None:
        row = await self._session.get(DeskSnapshotRow, account_id)
        if row is None:
            return None
        return Desk.model_validate(_apply_progress(dict(row.structure), dict(row.progress)))

    async def merge_and_save(self, account_id: UUID, incoming: Desk) -> Desk:
        row = await self._session.get(DeskSnapshotRow, account_id)
        structure, progress, merged_desk = merge(
            dict(row.structure) if row else None,
            dict(row.progress) if row else None,
            incoming,
        )
        now = datetime.now(timezone.utc)
        if row is None:
            row = DeskSnapshotRow(
                account_id=account_id,
                version=1,
                structure=structure,
                progress=progress,
                updated_at=now,
            )
            self._session.add(row)
        else:
            row.version += 1
            row.structure = structure
            row.progress = progress
            row.updated_at = now
        await self._session.commit()
        return merged_desk
