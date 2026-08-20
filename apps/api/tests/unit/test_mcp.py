from __future__ import annotations

from datetime import datetime

from facio_domain.desk import founding_desk
from facio_domain.models import CueOrigin, CueSurface
from facio_domain.tools import TOOL_NAMES, apply_tool

from facio_api.mcp.session import DeskSession

NOW = datetime(2026, 8, 15, 12, 0, 0)
ORIGIN = CueOrigin(chat_id="mcp")
CUE_ARGS = {
    "id": "push-ups-brace-agent",
    "subject_id": "push-ups",
    "kind": "correction",
    "text": "локти к рёбрам",
    "surface": "do-time",
}


def test_names_match_tool_names() -> None:
    session = DeskSession(founding_desk(now=NOW), now=NOW)
    assert session.names() == list(TOOL_NAMES)
    assert len(session.names()) == 16


def test_list_desk_matches_direct_apply() -> None:
    desk = founding_desk(now=NOW)
    session = DeskSession(desk.model_copy(deep=True), now=NOW)
    via_session = session.call("list_desk", {})
    via_apply = apply_tool(
        desk.model_copy(deep=True),
        "list_desk",
        {},
        pain=False,
        now=NOW,
        origin=ORIGIN,
    )
    assert via_session.data == via_apply.data


def test_add_cue_matches_direct_apply() -> None:
    desk = founding_desk(now=NOW)
    session = DeskSession(desk.model_copy(deep=True), now=NOW)
    via_session = session.call("add_cue", dict(CUE_ARGS))
    via_apply = apply_tool(
        desk.model_copy(deep=True),
        "add_cue",
        dict(CUE_ARGS),
        pain=False,
        now=NOW,
        origin=ORIGIN,
    )
    assert via_session.ok is via_apply.ok is True
    assert via_session.mutated is via_apply.mutated is True
    session_cue = next(row for row in session.desk.cues if row.id == CUE_ARGS["id"])
    apply_cue = next(row for row in via_apply.desk.cues if row.id == CUE_ARGS["id"])
    assert session_cue.id == apply_cue.id
    assert session_cue.text == apply_cue.text == CUE_ARGS["text"]
    assert session_cue.surface == apply_cue.surface == CueSurface.do_time
