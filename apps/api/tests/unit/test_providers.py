from __future__ import annotations

import pytest

from facio_api.config import (
    HAIKU_MODEL,
    Settings,
    UnknownModelError,
    canonical_model,
    provider_family,
)
from facio_api.providers.anthropic import (
    AnthropicProvider,
    anthropic_body_to_turn,
    openai_messages_to_anthropic,
    openai_tools_to_anthropic,
)
from facio_api.providers.factory import provider_for
from facio_api.providers.openai import OpenAIProvider
from facio_api.providers.scripted import ScriptedProvider
from facio_api.providers.types import LiveProviderError
from facio_api.talk.spec import tool_schemas


@pytest.mark.parametrize(
    ("name", "family", "resolved"),
    [
        ("haiku", "anthropic", HAIKU_MODEL),
        ("claude-haiku", "anthropic", HAIKU_MODEL),
        ("claude-haiku-4-5", "anthropic", "claude-haiku-4-5"),
        ("gpt-4o-mini", "openai", "gpt-4o-mini"),
        ("gpt", "openai", "gpt-4o-mini"),
        ("openai", "openai", "gpt-4o-mini"),
    ],
)
def test_model_name_selects_family(name: str, family: str, resolved: str) -> None:
    assert canonical_model(name) == resolved
    assert provider_family(name) == family


def test_unknown_model_name() -> None:
    with pytest.raises(UnknownModelError):
        provider_family("gemini-flash")


def test_scripted_ignores_keys() -> None:
    settings = Settings(
        talk_mode="scripted",
        model_name="haiku",
        openai_api_key="sk-openai",
        anthropic_api_key="sk-ant",
    )
    provider = provider_for(settings, "поясница забирает нагрузку")
    assert isinstance(provider, ScriptedProvider)


def test_live_haiku_uses_anthropic_even_if_openai_key_present() -> None:
    settings = Settings(
        talk_mode="live",
        model_name="haiku",
        openai_api_key="sk-openai",
        anthropic_api_key="sk-ant-test",
    )
    provider = provider_for(settings, "hi")
    assert isinstance(provider, AnthropicProvider)


def test_live_gpt_uses_openai_even_if_anthropic_key_present() -> None:
    settings = Settings(
        talk_mode="live",
        model_name="gpt-4o-mini",
        openai_api_key="sk-openai",
        anthropic_api_key="sk-ant-test",
    )
    provider = provider_for(settings, "hi")
    assert isinstance(provider, OpenAIProvider)


def test_live_haiku_without_anthropic_key() -> None:
    settings = Settings(
        talk_mode="live",
        model_name="haiku",
        openai_api_key="sk-openai",
        anthropic_api_key=None,
    )
    with pytest.raises(LiveProviderError, match="anthropic key missing"):
        provider_for(settings, "hi")


def test_live_unknown_model() -> None:
    settings = Settings(
        talk_mode="live",
        model_name="gemini-flash",
        openai_api_key="sk-openai",
        anthropic_api_key="sk-ant",
    )
    with pytest.raises(LiveProviderError, match="unknown model"):
        provider_for(settings, "hi")


def test_live_gpt_without_openai_key() -> None:
    settings = Settings(
        talk_mode="live",
        model_name="gpt-4o-mini",
        openai_api_key=None,
        anthropic_api_key="sk-ant-test",
    )
    with pytest.raises(LiveProviderError, match="openai key missing"):
        provider_for(settings, "hi")


def test_openai_tools_become_anthropic_input_schema() -> None:
    converted = openai_tools_to_anthropic(tool_schemas())
    add_cue = next(row for row in converted if row["name"] == "add_cue")
    assert "parameters" not in add_cue
    assert add_cue["input_schema"]["type"] == "object"
    assert "surface" in add_cue["input_schema"]["properties"]


def test_openai_messages_split_system_and_merge_tool_results() -> None:
    system, chat = openai_messages_to_anthropic(
        [
            {"role": "system", "content": "You are Facio."},
            {"role": "system", "content": "Desk now."},
            {"role": "user", "content": "hi"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "add_cue", "arguments": '{"subject_id": "push-ups"}'},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call_1", "content": '{"ok": true}'},
            {"role": "tool", "tool_call_id": "call_2", "content": '{"ok": false}'},
        ]
    )
    assert [block["text"] for block in system] == ["You are Facio.", "Desk now."]
    assert chat[0] == {"role": "user", "content": "hi"}
    assert chat[1]["role"] == "assistant"
    assert chat[1]["content"][0]["type"] == "tool_use"
    assert chat[1]["content"][0]["name"] == "add_cue"
    assert chat[1]["content"][0]["input"] == {"subject_id": "push-ups"}
    assert chat[2]["role"] == "user"
    assert [block["tool_use_id"] for block in chat[2]["content"]] == ["call_1", "call_2"]


def test_anthropic_body_to_turn_reads_tool_use() -> None:
    turn = anthropic_body_to_turn(
        {
            "content": [
                {"type": "text", "text": "пишу на стол"},
                {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "add_cue",
                    "input": {"subject_id": "push-ups", "surface": "do-time"},
                },
            ]
        }
    )
    assert turn.text == "пишу на стол"
    assert turn.tool_calls[0].name == "add_cue"
    assert turn.tool_calls[0].arguments["surface"] == "do-time"


async def test_anthropic_complete_posts_messages_api(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def json(self) -> dict[str, object]:
            return {"content": [{"type": "text", "text": "готово"}], "stop_reason": "end_turn"}

        def raise_for_status(self) -> None:
            return None

    class FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            del args

        async def post(self, url: str, headers: dict[str, str], json: dict[str, object]) -> FakeResponse:
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr("facio_api.providers.anthropic.httpx.AsyncClient", FakeClient)
    settings = Settings(
        talk_mode="live",
        model_name="haiku",
        anthropic_api_key="sk-ant-test",
        openai_api_key="sk-should-not-be-sent",
    )
    turn = await AnthropicProvider(settings).complete(
        [{"role": "system", "content": "rules"}, {"role": "user", "content": "hi"}],
        tool_schemas(),
    )
    assert turn.text == "готово"
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers["x-api-key"] == "sk-ant-test"
    assert "Authorization" not in headers
    body = captured["json"]
    assert isinstance(body, dict)
    assert body["model"] == HAIKU_MODEL
    # One block, and it carries the breakpoint: tools render before system,
    # so the marker here caches the schemas and the prompt together.
    assert body["system"] == [
        {"type": "text", "text": "rules", "cache_control": {"type": "ephemeral"}}
    ]


async def test_openai_complete_uses_openai_key(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def json(self) -> dict[str, object]:
            return {"choices": [{"message": {"content": "ok", "tool_calls": []}}]}

        def raise_for_status(self) -> None:
            return None

    class FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            del args

        async def post(self, url: str, headers: dict[str, str], json: dict[str, object]) -> FakeResponse:
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr("facio_api.providers.openai.httpx.AsyncClient", FakeClient)
    settings = Settings(
        talk_mode="live",
        model_name="gpt-4o-mini",
        openai_api_key="sk-openai",
        anthropic_api_key="sk-ant-should-not-be-sent",
    )
    turn = await OpenAIProvider(settings).complete(
        [{"role": "user", "content": "hi"}],
        tool_schemas(),
    )
    assert turn.text == "ok"
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"] == "Bearer sk-openai"
    body = captured["json"]
    assert isinstance(body, dict)
    assert body["model"] == "gpt-4o-mini"
