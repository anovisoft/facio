"""The cache breakpoint, and the prefix it depends on.

Prompt caching is a prefix match: one byte earlier in the rendered prompt and
everything after it stops being reusable. It fails silently — no error, just a
larger bill — so the shape of the prefix is worth a test of its own.
"""

from __future__ import annotations

import json
from typing import Any

from facio_api.providers.anthropic import (
    anthropic_body_to_turn,
    openai_messages_to_anthropic,
    system_blocks,
)
from facio_api.talk.loop import _messages
from facio_api.talk.schemas import TalkSelection, TalkTurnRequest
from facio_domain.desk import founding_desk


def _request(**over: Any) -> TalkTurnRequest:
    body: dict[str, Any] = {
        "utterance": "hi",
        "desk": json.loads(founding_desk().model_dump_json()),
        "thread": [],
    }
    body.update(over)
    return TalkTurnRequest.model_validate(body)


def _stable(body: TalkTurnRequest) -> str:
    system, _ = openai_messages_to_anthropic(_messages(body, body.utterance, pain=False))
    return system[0]["text"]


def test_breakpoint_sits_on_the_first_system_block_only() -> None:
    blocks = system_blocks(["prompt", "desk", "selection"])
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in blocks[1]
    assert "cache_control" not in blocks[2]


def test_empty_system_makes_no_blocks() -> None:
    assert system_blocks([]) == []


def test_the_stable_prefix_survives_a_different_desk() -> None:
    """The desk changes every turn. It must sit after the breakpoint."""
    plain = _request()
    changed_desk = json.loads(founding_desk().model_dump_json())
    changed_desk["subjects"][0]["title"] = "отжимания на брусьях"
    assert _stable(plain) == _stable(_request(desk=changed_desk))


def test_the_stable_prefix_survives_a_selection_and_a_focus() -> None:
    plain = _request()
    with_selection = _request(
        selection=TalkSelection(quote="не роняй таз", widget_id="push-ups-counter").model_dump(),
        focused_widget_id="push-ups-counter",
    )
    assert _stable(plain) == _stable(with_selection)


def test_each_language_gets_its_own_prefix() -> None:
    """Two entries, on purpose: the language line is part of what is cached."""
    assert _stable(_request(locale="ru")) != _stable(_request(locale="en"))


def test_the_desk_is_not_in_the_cached_block() -> None:
    system, _ = openai_messages_to_anthropic(_messages(_request(), "hi", pain=False))
    assert "Стол сейчас" not in system[0]["text"]
    assert any("Стол сейчас" in block["text"] for block in system[1:])


def test_usage_comes_back_so_cache_hits_can_be_checked() -> None:
    turn = anthropic_body_to_turn(
        {
            "content": [{"type": "text", "text": "ок"}],
            "usage": {"input_tokens": 12, "cache_read_input_tokens": 3400},
        }
    )
    assert turn.usage["cache_read_input_tokens"] == 3400


def test_usage_is_empty_when_the_vendor_sends_none() -> None:
    assert anthropic_body_to_turn({"content": []}).usage == {}
