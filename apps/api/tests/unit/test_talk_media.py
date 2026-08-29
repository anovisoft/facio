"""R6: a link on a cue must be one the person actually wrote.

The trap is named in [06] #23 and in its table: «Model-invented image URLs —
hallucinated links, dead hotlinks, and a wrong picture on a movement is worse
than none». Asking the model nicely is not a lock, so the turn checks: the URL
has to occur **verbatim** in the person's own words — this utterance or their
own messages in the thread. It does not, and the call comes back named
(`media_not_in_conversation`), the desk is untouched, and the turn writes itself
right on the next round — the shape `quote_required` and `surface_required`
already proved.

Nothing here is repaired on the model's behalf: no trimming, no case folding,
no scheme guessing. Fixing a URL for it is the same silent desk edit as filling
in a quote (never-do AI #2). Fake provider, no network.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from facio_domain.desk import founding_desk
from facio_domain.models import CueSurface
from facio_domain.tools import INVALID_MEDIA

from facio_api.providers.types import ModelToolCall, ModelTurn
from facio_api.talk.loop import MEDIA_NOT_IN_CONVERSATION, run_turn
from facio_api.talk.schemas import Locale, TalkTurnRequest, ThreadMessage

NOW = datetime(2026, 8, 15, 12, 0, 0)
HER_LINK = "https://youtu.be/9x1FZrq3kQo"
INVENTED = "https://youtube.com/watch?v=perfect-pushup-form"


class SequenceProvider:
    """Plays scripted turns; after the script, closing text only."""

    def __init__(self, turns: list[ModelTurn]) -> None:
        self._turns = list(turns)
        self.complete_count = 0

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelTurn:
        del messages, tools
        if self.complete_count >= len(self._turns):
            return ModelTurn(text="Готово.")
        turn = self._turns[self.complete_count]
        self.complete_count += 1
        return turn


def _request(
    utterance: str,
    *,
    thread: list[ThreadMessage] | None = None,
    locale: Locale = "ru",
) -> TalkTurnRequest:
    return TalkTurnRequest(
        utterance=utterance,
        desk=founding_desk(now=NOW),
        thread=thread or [],
        thread_id="media",
        now=NOW,
        locale=locale,
    )


def _cue_call(call_id: str, media: dict[str, Any] | None, cue_id: str = "push-ups-media-talk") -> ModelToolCall:
    arguments: dict[str, Any] = {
        "id": cue_id,
        "subject_id": "push-ups",
        "step_id": "rep-1",
        "kind": "clarification",
        "text": "опускайся медленно, три-четыре секунды вниз",
        "surface": "on-demand",
        "quote": "негативные повторения",
    }
    if media is not None:
        arguments["media"] = media
    return ModelToolCall(id=call_id, name="add_cue", arguments=arguments)


async def _play(provider: SequenceProvider, request: TalkTurnRequest):
    return await run_turn(request, provider, now=NOW)


async def test_the_link_from_this_utterance_lands_unchanged() -> None:
    provider = SequenceProvider([ModelTurn(tool_calls=[_cue_call("c1", {"kind": "link", "url": HER_LINK})])])
    result = await _play(provider, _request(f"вот видео: {HER_LINK} — что это значит?"))

    call = result.tool_calls[0]
    assert call.ok is True
    assert call.error is None
    cue = next(row for row in result.desk.cues if row.id == "push-ups-media-talk")
    assert cue.media is not None
    assert cue.media.kind == "link"
    # Character for character: the desk carries her URL, not a tidied one.
    assert cue.media.url == HER_LINK
    assert cue.surface == CueSurface.on_demand


async def test_a_link_from_an_earlier_message_of_hers_still_counts() -> None:
    """She pasted it a message ago and asked about it now. Same conversation,
    same words — the answer may still carry it."""
    provider = SequenceProvider([ModelTurn(tool_calls=[_cue_call("c1", {"kind": "link", "url": HER_LINK})])])
    result = await _play(
        provider,
        _request(
            "а что тут главное?",
            thread=[ThreadMessage(role="user", text=f"нашла ролик: {HER_LINK}")],
        ),
    )

    assert result.tool_calls[0].ok is True
    cue = next(row for row in result.desk.cues if row.id == "push-ups-media-talk")
    assert cue.media is not None
    assert cue.media.url == HER_LINK


async def test_a_url_the_model_invented_is_refused_and_nothing_lands() -> None:
    provider = SequenceProvider([ModelTurn(tool_calls=[_cue_call("c1", {"kind": "link", "url": INVENTED})])])
    result = await _play(provider, _request("как понять, что я делаю это правильно?"))

    call = result.tool_calls[0]
    assert call.ok is False
    assert call.error == MEDIA_NOT_IN_CONVERSATION
    assert result.mutated is False
    assert result.desk.cues == founding_desk(now=NOW).cues
    assert result.snapshots == []


async def test_the_refusal_leaves_the_turn_a_round_to_write_the_cue_plainly() -> None:
    """The cue itself is not lost: the second round drops the media and lands.
    The conclusion survives; only the invented link does not."""
    provider = SequenceProvider(
        [
            ModelTurn(tool_calls=[_cue_call("c1", {"kind": "link", "url": INVENTED}, "push-ups-invented")]),
            ModelTurn(tool_calls=[_cue_call("c2", None, "push-ups-plain")]),
        ]
    )
    result = await _play(provider, _request("как понять, что я делаю это правильно?"))

    first, second = result.tool_calls
    assert first.error == MEDIA_NOT_IN_CONVERSATION
    assert second.ok is True
    assert all(row.id != "push-ups-invented" for row in result.desk.cues)
    landed = next(row for row in result.desk.cues if row.id == "push-ups-plain")
    # A step must be executable without media (04) — the cue is complete as is.
    assert landed.media is None
    assert landed.text
    assert result.mutated is True


async def test_a_link_the_assistant_itself_produced_does_not_count() -> None:
    """Otherwise the check launders inventions: the model quotes its own
    hallucination back from the transcript and it becomes «the person's»."""
    provider = SequenceProvider([ModelTurn(tool_calls=[_cue_call("c1", {"kind": "link", "url": INVENTED})])])
    result = await _play(
        provider,
        _request(
            "давай его",
            thread=[ThreadMessage(role="assistant", text=f"вот хорошее видео: {INVENTED}")],
        ),
    )

    assert result.tool_calls[0].error == MEDIA_NOT_IN_CONVERSATION
    assert result.mutated is False


async def test_a_url_that_only_almost_matches_is_still_refused() -> None:
    """One character off is a different video — and a wrong picture on a
    movement is worse than none ([06] #23). Nothing is corrected for the model."""
    provider = SequenceProvider(
        [ModelTurn(tool_calls=[_cue_call("c1", {"kind": "link", "url": "https://youtu.be/9x1FZrq3kQ0"})])]
    )
    result = await _play(provider, _request(f"вот видео: {HER_LINK}"))

    assert result.tool_calls[0].error == MEDIA_NOT_IN_CONVERSATION
    assert result.mutated is False


async def test_the_check_does_not_touch_ordinary_cues() -> None:
    provider = SequenceProvider([ModelTurn(tool_calls=[_cue_call("c1", None)])])
    result = await _play(provider, _request("поясница забирает нагрузку"))

    assert result.tool_calls[0].ok is True
    cue = next(row for row in result.desk.cues if row.id == "push-ups-media-talk")
    assert cue.media is None


async def test_her_own_photo_is_not_a_url_and_is_not_checked_against_the_text() -> None:
    """`photo` is her picture of that machine, handed over by the client — the
    thing 05 calls the feature, as opposed to our image library. Its ref is not
    a link the model can hallucinate into an image, so the URL check leaves it
    to the law."""
    provider = SequenceProvider(
        [ModelTurn(tool_calls=[_cue_call("c1", {"kind": "photo", "ref": "local://photo/17"})])]
    )
    result = await _play(provider, _request("какой тренажёр мой?"))

    assert result.tool_calls[0].ok is True
    cue = next(row for row in result.desk.cues if row.id == "push-ups-media-talk")
    assert cue.media is not None
    assert cue.media.kind == "photo"
    assert cue.media.ref == "local://photo/17"


async def test_two_media_items_stay_the_law_s_refusal_by_its_own_name() -> None:
    """At most one per cue (04). A list is not trimmed down to its first item,
    and the turn is told which field was wrong — `invalid_media`, not the URL
    check's name."""
    both_at_once = _cue_call("c1", None)
    both_at_once.arguments["media"] = [
        {"kind": "link", "url": HER_LINK},
        {"kind": "photo", "ref": "local://photo/17"},
    ]
    provider = SequenceProvider([ModelTurn(tool_calls=[both_at_once])])
    result = await _play(provider, _request(f"вот видео: {HER_LINK} и фото"))

    call = result.tool_calls[0]
    assert call.ok is False
    assert call.error == INVALID_MEDIA
    assert result.mutated is False


async def test_the_english_half_refuses_the_same_way() -> None:
    provider = SequenceProvider(
        [ModelTurn(tool_calls=[_cue_call("c1", {"kind": "link", "url": INVENTED})])]
    )
    result = await _play(
        provider, _request("how do I know I am doing this right?", locale="en")
    )

    assert result.tool_calls[0].error == MEDIA_NOT_IN_CONVERSATION
    assert result.mutated is False
