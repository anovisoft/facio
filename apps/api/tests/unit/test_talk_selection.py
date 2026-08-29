"""R3: a selected phrase reaches the turn, and only a real binding makes a cue.

The lock the tests hold is the one RFC 05 states plainly: a selection with a
bound subject leaves a `clarification` cue behind a `?`; a selection with no
bound subject leaves text and nothing else. The binding comes from the desk,
never from the model's guess about which practice was nearby.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from facio_domain.desk import founding_desk
from facio_domain.models import CueKind, CueSurface

from facio_api.providers.types import ModelToolCall, ModelTurn
from facio_api.talk.loop import run_turn, selection_line, selection_subject_id
from facio_api.talk.schemas import TalkSelection, TalkTurnRequest
from facio_api.talk.spec import SYSTEM_PROMPT

NOW = datetime(2026, 8, 15, 12, 0, 0)


class RecordingProvider:
    """Plays a script and keeps what it was shown."""

    def __init__(self, turns: list[ModelTurn]) -> None:
        self._turns = list(turns)
        self.messages_at: list[list[dict[str, Any]]] = []

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelTurn:
        del tools
        self.messages_at.append([dict(row) for row in messages])
        if not self._turns:
            return ModelTurn(text="Готово.")
        return self._turns.pop(0)


def _request(
    utterance: str,
    selection: TalkSelection | None = None,
    *,
    focused_widget_id: str | None = None,
) -> TalkTurnRequest:
    return TalkTurnRequest(
        utterance=utterance,
        desk=founding_desk(now=NOW),
        thread=[],
        thread_id="selection",
        now=NOW,
        selection=selection,
        focused_widget_id=focused_widget_id,
    )


def _system(provider: RecordingProvider) -> list[str]:
    return [str(row["content"]) for row in provider.messages_at[0] if row.get("role") == "system"]


# --- what the desk says the selection is bound to -------------------------


def test_subject_id_wins_when_it_is_on_the_desk() -> None:
    body = _request("что это значит?", TalkSelection(quote="таз", subject_id="push-ups"))
    assert selection_subject_id(body) == "push-ups"


def test_widget_id_resolves_through_the_desk() -> None:
    body = _request("что это значит?", TalkSelection(quote="таз", widget_id="push-ups-counter"))
    assert selection_subject_id(body) == "push-ups"


def test_focused_widget_binds_when_the_selection_named_nothing() -> None:
    body = _request(
        "что это значит?",
        TalkSelection(quote="таз"),
        focused_widget_id="bike-reminder",
    )
    assert selection_subject_id(body) == "bike"


def test_a_subject_that_is_not_on_the_desk_is_not_a_binding() -> None:
    body = _request("что это значит?", TalkSelection(quote="экономичность", subject_id="running"))
    assert selection_subject_id(body) is None


def test_a_widget_that_is_not_on_the_desk_is_not_a_binding() -> None:
    body = _request("что это значит?", TalkSelection(quote="экономичность", widget_id="ghost"))
    assert selection_subject_id(body) is None


def test_nothing_named_is_no_binding_at_all() -> None:
    """No fallback to the default subject: guessing would manufacture the orphan."""
    body = _request("что это значит?", TalkSelection(quote="беговая экономичность"))
    assert selection_subject_id(body) is None


# --- the line the model is shown ------------------------------------------


def test_bound_line_asks_for_on_demand_and_the_quote() -> None:
    body = _request(
        "что это значит?",
        TalkSelection(quote="не роняй таз", widget_id="push-ups-counter", step_id="rep-1"),
    )
    line = selection_line(body)
    assert "не роняй таз" in line
    assert "push-ups" in line
    assert "clarification" in line
    assert "on-demand" in line
    assert "step_id rep-1" in line


def test_bound_line_without_a_step_says_nothing_about_one() -> None:
    body = _request("что это значит?", TalkSelection(quote="таз", subject_id="push-ups"))
    line = selection_line(body)
    assert "step" not in line


def test_orphan_line_forbids_the_write() -> None:
    body = _request("что это значит?", TalkSelection(quote="беговая экономичность"))
    line = selection_line(body)
    assert "беговая экономичность" in line
    assert "Do not call add_cue" in line
    assert "on-demand" not in line


async def test_a_turn_without_a_selection_carries_no_selection_line() -> None:
    provider = RecordingProvider([ModelTurn(text="Ок."), ModelTurn(text="Ок.")])
    await run_turn(_request("держи корпус"), provider, now=NOW)
    assert not any("selected this phrase" in row for row in _system(provider))


# --- the whole turn -------------------------------------------------------


async def test_bound_selection_line_rides_the_turn() -> None:
    provider = RecordingProvider(
        [
            ModelTurn(
                text=None,
                tool_calls=[
                    ModelToolCall(
                        id="call_1",
                        name="add_cue",
                        arguments={
                            "id": "push-ups-hips-live",
                            "subject_id": "push-ups",
                            "step_id": "rep-1",
                            "kind": "clarification",
                            "text": "таз в одну линию с плечами",
                            "surface": "on-demand",
                            "quote": "не роняй таз",
                        },
                    )
                ],
            ),
            ModelTurn(text="Таз в одну линию с плечами."),
        ]
    )
    body = _request(
        "что это значит?",
        TalkSelection(quote="не роняй таз", widget_id="push-ups-counter", step_id="rep-1"),
    )
    result = await run_turn(body, provider, now=NOW)
    assert any("не роняй таз" in row for row in _system(provider))
    cue = next(row for row in result.desk.cues if row.id == "push-ups-hips-live")
    assert cue.kind == CueKind.clarification
    assert cue.surface == CueSurface.on_demand
    assert cue.step_id == "rep-1"
    assert cue.quote == "не роняй таз"


async def test_an_orphan_selection_that_the_model_tries_to_bind_anyway_is_refused() -> None:
    """Belt on top of the mouth rule: an unknown subject never becomes a cue."""
    provider = RecordingProvider(
        [
            ModelTurn(
                text=None,
                tool_calls=[
                    ModelToolCall(
                        id="call_1",
                        name="add_cue",
                        arguments={
                            "subject_id": "running",
                            "kind": "clarification",
                            "text": "сколько сил на километр",
                            "surface": "on-demand",
                            "quote": "беговая экономичность",
                        },
                    )
                ],
            ),
            ModelTurn(text="Сколько сил уходит на километр."),
        ]
    )
    body = _request("что это значит?", TalkSelection(quote="беговая экономичность"))
    result = await run_turn(body, provider, now=NOW)
    assert result.mutated is False
    assert result.snapshots == []
    assert result.tool_calls[0].ok is False
    assert result.tool_calls[0].error == "not_found"
    assert result.desk.cues == founding_desk(now=NOW).cues


# --- the prompt bullet ----------------------------------------------------


def _selection_bullet() -> str:
    return next(row for row in SYSTEM_PROMPT.splitlines() if row.startswith("- A selected phrase"))


def test_selection_bullet_is_bilingual_and_on_demand() -> None:
    bullet = _selection_bullet()
    assert "kind clarification" in bullet
    assert "surface on-demand" in bullet
    assert "step_id" in bullet
    assert "quote copied exactly" in bullet
    assert "не роняй таз" in bullet
    assert "don't let the hips sag" in bullet
    # Never inline at do-time: rep one has to stay readable (04, P9).
    assert "Never do-time" in bullet


def test_selection_bullet_says_text_only_when_nothing_is_bound() -> None:
    bullet = _selection_bullet()
    assert "Bound to nothing — text only" in bullet
    assert "no add_cue" in bullet


def test_selection_bullet_sits_last_so_it_does_not_crowd_the_timing_rules() -> None:
    """Measured on live Haiku: the bullet placed among the cue rules cost the
    timing cue on «напомни в 19, в 21 сплю» (kind="timing" refusals). At the end
    of the list the reminder locks hold. Position is load-bearing, not taste.

    R6 put the media bullet directly after it — the two are one subject, the
    answer to a selected phrase and what may ride with it — and the catalog
    bullet stays last. The timing rules keep the whole middle to themselves.
    """
    rows = [row for row in SYSTEM_PROMPT.splitlines() if row.startswith("- ")]
    assert rows.index(_selection_bullet()) == len(rows) - 3
    assert rows[-2].startswith("- Media on a cue")
    assert rows[-1].startswith("- Widget type only from the catalog")


def test_add_cue_schema_advertises_step_id_and_quote() -> None:
    from facio_api.talk.spec import tool_schemas

    add_cue = next(row["function"] for row in tool_schemas() if row["function"]["name"] == "add_cue")
    properties = add_cue["parameters"]["properties"]
    assert "step_id" in properties
    assert "quote" in properties
    assert set(add_cue["parameters"]["required"]) == {"subject_id", "kind", "text", "surface"}


def test_add_cue_schema_offers_media_in_the_law_s_own_two_shapes() -> None:
    """R6: `media` is advertised so the link the **person** sent can ride her
    cue. It is optional — a step must be executable without media (04) — and it
    is `LinkMedia` / `PhotoMedia`, never a second shape invented for the wire.
    The URL is checked against her words, so the schema is an invitation, not
    the lock ([06] #23)."""
    from facio_api.talk.spec import tool_schemas

    add_cue = next(row["function"] for row in tool_schemas() if row["function"]["name"] == "add_cue")
    media = add_cue["parameters"]["properties"]["media"]
    assert media["type"] == "object"
    assert "media" not in add_cue["parameters"]["required"]
    assert media["properties"]["kind"]["enum"] == ["link", "photo"]
    assert set(media["properties"]) == {"kind", "url", "ref"}
    assert media["required"] == ["kind"]
    assert media["additionalProperties"] is False
    assert "media_not_in_conversation" in media["description"]


def test_add_cue_media_shapes_match_the_law() -> None:
    """The wire shape is the law's, field for field — a schema that drifted
    from `facio_domain.models` would only teach the model calls that come back
    `invalid_media`."""
    from facio_domain.models import LinkMedia, PhotoMedia

    from facio_api.talk.spec import tool_schemas

    add_cue = next(row["function"] for row in tool_schemas() if row["function"]["name"] == "add_cue")
    media = add_cue["parameters"]["properties"]["media"]
    advertised = set(media["properties"])
    assert advertised == set(LinkMedia.model_fields) | set(PhotoMedia.model_fields)
