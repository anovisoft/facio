from __future__ import annotations

from datetime import datetime

from facio_domain.chips import MAX_CHIPS
from facio_domain.desk import founding_desk
from facio_domain.models import CueOrigin, CueSurface
from facio_domain.tools import TOOL_NAMES, apply_tool

from facio_api.mcp.server import mcp_tools
from facio_api.mcp.session import DeskSession
from facio_api.talk.spec import tool_schemas

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
    assert len(session.names()) == len(TOOL_NAMES)


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


def test_every_advertised_name_has_a_schema_and_every_schema_a_name() -> None:
    """The two lists are one list. `mcp_tools` looks each name up in the talk
    schemas, so a tool added to `TOOL_NAMES` without one dies at import time on
    stdio and would otherwise be advertised to the vendor and never to MCP.
    This is what pins the count: it grows here, in `TOOL_NAMES`, and in the
    schemas together or not at all.
    """
    advertised = [row["function"]["name"] for row in tool_schemas()]
    assert advertised == list(TOOL_NAMES)
    assert [row.name for row in mcp_tools()] == list(TOOL_NAMES)


def test_search_facts_is_advertised_as_a_read_that_needs_a_query() -> None:
    """В3.3: the mouth may look through the person's own facts. `query` is
    required — an empty one comes back `query_required` — and `subject_id` only
    narrows it. Nothing here writes."""
    schema = next(row["function"] for row in tool_schemas() if row["function"]["name"] == "search_facts")
    parameters = schema["parameters"]
    assert set(parameters["properties"]) == {"query", "subject_id"}
    assert parameters["required"] == ["query"]
    assert parameters["additionalProperties"] is False


def test_search_facts_through_the_session_leaves_the_desk_alone() -> None:
    session = DeskSession(founding_desk(now=NOW), now=NOW)
    before = session.desk.model_copy(deep=True)
    outcome = session.call("search_facts", {"query": "зал"})
    assert outcome.ok is True
    assert outcome.mutated is False
    assert session.desk == before
    assert [row["cue_id"] for row in outcome.data["facts"]] == ["bike-gym-hours"]


def test_offer_chips_is_advertised_last_and_capped_at_three() -> None:
    """Q35: the row above the composer is text and nothing else.

    `chips` carries strings — no id, no action, no callback — because a chip
    with one of those is a button that decides for the person (never-do AI #2).
    It sits last for the same reason `search_facts` does: the schemas render
    ahead of the system prompt and the vendors cache on that prefix.
    """
    assert TOOL_NAMES[-1] == "offer_chips"
    assert [row["function"]["name"] for row in tool_schemas()][-1] == "offer_chips"
    schema = next(row["function"] for row in tool_schemas() if row["function"]["name"] == "offer_chips")
    parameters = schema["parameters"]
    assert set(parameters["properties"]) == {"chips"}
    assert parameters["required"] == ["chips"]
    assert parameters["additionalProperties"] is False
    chips = parameters["properties"]["chips"]
    assert chips["items"] == {"type": "string"}
    assert (chips["minItems"], chips["maxItems"]) == (1, MAX_CHIPS)


def test_offering_chips_through_the_session_leaves_the_desk_alone() -> None:
    session = DeskSession(founding_desk(now=NOW), now=NOW)
    before = session.desk.model_copy(deep=True)
    outcome = session.call("offer_chips", {"chips": ["Напомни завтра"]})
    assert outcome.ok is True
    assert outcome.mutated is False
    assert session.desk == before
    assert outcome.data == {"chips": ["Напомни завтра"]}
