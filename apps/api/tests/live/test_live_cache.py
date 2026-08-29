"""The prompt cache, checked against the vendor.

Caching fails silently: no error, no wrong answer, just four times the bill on
every turn. The only ground truth is `usage` on the round the provider already
returns (`ModelTurn.usage`), so the guard is two identical rounds in a row —
the second one has to come back as a read.

A prefix below the model's minimum cacheable size cannot cache, whatever the
code does. That case is a `skip` that says the numbers out loud, never a quiet
`pass`: a silent pass here is exactly the month-long blindness this file exists
to prevent.
"""

from __future__ import annotations

import json
from datetime import datetime

import httpx
import pytest

from facio_domain.desk import founding_desk

from facio_api.config import Settings
from facio_api.providers.anthropic import (
    ANTHROPIC_VERSION,
    openai_messages_to_anthropic,
    openai_tools_to_anthropic,
)
from facio_api.providers.factory import provider_for
from facio_api.talk.loop import _messages
from facio_api.talk.schemas import TalkTurnRequest
from facio_api.talk.spec import tool_schemas

pytestmark = pytest.mark.live

NOW = datetime(2026, 8, 15, 12, 0, 0)
UTTERANCE = "запиши зал"

# Anthropic's minimum cacheable prefix, per model. It is not monotonic across
# generations — Haiku 4.5 needs 4096 where Sonnet 5 needs 1024 — so it is a
# table, not a constant, and an unlisted model skips instead of guessing.
MIN_CACHEABLE_PREFIX: dict[str, int] = {
    "claude-haiku-4-5": 4096,
    "claude-opus-4-5": 4096,
    "claude-opus-4-6": 4096,
    "claude-opus-4-7": 2048,
    "claude-haiku-3-5": 2048,
    "claude-opus-4-8": 1024,
    "claude-sonnet-5": 1024,
    "claude-sonnet-4-6": 1024,
    "claude-opus-5": 512,
}


def _turn_messages() -> tuple[list[dict], list[dict]]:
    body = TalkTurnRequest(
        utterance=UTTERANCE,
        desk=founding_desk(now=NOW),
        thread=[],
        thread_id="live-cache",
        now=NOW,
        locale="ru",
    )
    return _messages(body, UTTERANCE, pain=False), tool_schemas()


def _cacheable_prefix_tokens(settings: Settings, messages: list[dict], tools: list[dict]) -> int:
    """What the vendor counts for tools + the one block the breakpoint sits on.

    `count_tokens` is free and needs no completion. It reads a little high for
    this purpose — the per-request scaffold it adds is not part of the segment
    the cache actually keys on — so it is used to tell "hopelessly short" from
    "should be caching", not as a second source of truth about a hit.
    """
    system, _ = openai_messages_to_anthropic(messages)
    response = httpx.post(
        f"{settings.anthropic_base_url.rstrip('/')}/v1/messages/count_tokens",
        headers={
            "x-api-key": settings.anthropic_api_key or "",
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
        json={
            "model": settings.resolved_model,
            "messages": [{"role": "user", "content": "."}],
            "system": [{"type": "text", "text": system[0]["text"]}],
            "tools": openai_tools_to_anthropic(tools),
        },
        timeout=60.0,
    )
    response.raise_for_status()
    return int(response.json()["input_tokens"])


async def test_a_second_identical_round_is_read_from_the_cache(live_settings: Settings) -> None:
    if live_settings.family != "anthropic":
        pytest.skip(f"prompt caching guard is Anthropic-only; model family is {live_settings.family}")
    model = live_settings.resolved_model
    floor = MIN_CACHEABLE_PREFIX.get(model)
    if floor is None:
        pytest.skip(
            f"no minimum cacheable prefix recorded for {model}; add it to MIN_CACHEABLE_PREFIX "
            "before trusting a cache result on this model"
        )

    messages, tools = _turn_messages()
    provider = provider_for(live_settings, UTTERANCE)
    first = await provider.complete(list(messages), tools)
    second = await provider.complete(list(messages), tools)
    read = int(second.usage.get("cache_read_input_tokens") or 0)
    if read > 0:
        # Written on one round, read back on the next: the fixed half of a turn
        # is being paid for once instead of every time.
        assert int(first.usage.get("cache_creation_input_tokens") or 0) + read > 0
        return

    prefix = _cacheable_prefix_tokens(live_settings, messages, tools)
    if prefix < floor:
        pytest.skip(
            f"{model} caches nothing below {floor} tokens and the cached prefix measures "
            f"{prefix} — the turn is paying full price for tools and prompt on every round. "
            "Grow the cached prefix (tool descriptions, the system prompt) or run a model "
            f"with a lower floor. usage: {json.dumps(second.usage, ensure_ascii=False)}"
        )
    raise AssertionError(
        f"{model} read nothing back from the cache on an identical second round, and the cached "
        f"prefix measures {prefix} tokens against a floor of {floor} — either the breakpoint has "
        "stopped covering a stable prefix (something per-request drifted into the first system "
        f"block) or the prefix is sitting on the floor. usage: "
        f"{json.dumps(second.usage, ensure_ascii=False)}"
    )
