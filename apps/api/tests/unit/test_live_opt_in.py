"""Unit coverage for live opt-in / missing-key skip. No vendor, no keys printed."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from facio_api.config import Settings
from support.live import force_live, live_env_files, live_opted_in, skip_without_vendor_key


class _Config:
    def __init__(self, *, live_flag: bool, markexpr: str | None) -> None:
        self._live_flag = live_flag
        self.option = SimpleNamespace(markexpr=markexpr)

    def getoption(self, name: str) -> bool:
        if name in {"--live", "live"}:
            return self._live_flag
        raise AssertionError(name)


def _settings(**kwargs: object) -> Settings:
    return Settings(_env_file=None, **kwargs)


def test_opt_in_off_by_default() -> None:
    assert live_opted_in(_Config(live_flag=False, markexpr="")) is False
    assert live_opted_in(_Config(live_flag=False, markexpr=None)) is False
    assert live_opted_in(_Config(live_flag=False, markexpr="not live")) is False
    assert live_opted_in(_Config(live_flag=False, markexpr="live or unit")) is False


def test_opt_in_via_flag_or_exact_markexpr() -> None:
    assert live_opted_in(_Config(live_flag=True, markexpr="")) is True
    assert live_opted_in(_Config(live_flag=False, markexpr="live")) is True
    assert live_opted_in(_Config(live_flag=False, markexpr=" live ")) is True


def test_force_live_ignores_scripted_keeps_model() -> None:
    loaded = _settings(
        talk_mode="scripted",
        model_name="haiku",
        openai_api_key=None,
        anthropic_api_key=None,
    )
    settings = force_live(loaded)
    assert settings.talk_mode == "live"
    assert settings.model_name == "haiku"
    assert settings.anthropic_api_key is None
    assert settings.openai_api_key is None


def test_skip_without_vendor_key_skips() -> None:
    settings = force_live(
        _settings(
            talk_mode="scripted",
            model_name="haiku",
            openai_api_key=None,
            anthropic_api_key=None,
        )
    )
    with pytest.raises(pytest.skip.Exception, match="anthropic key missing"):
        skip_without_vendor_key(settings)


def test_live_env_files_are_existing_dotenv_paths() -> None:
    for path in live_env_files():
        assert path.endswith(".env")
        assert Path(path).is_file()


def test_skip_without_vendor_key_keeps_settings_when_present() -> None:
    settings = force_live(
        _settings(
            talk_mode="scripted",
            model_name="gpt-4o-mini",
            openai_api_key="sk-test-not-used",
            anthropic_api_key=None,
        )
    )
    kept = skip_without_vendor_key(settings)
    assert kept is settings
    assert kept.talk_mode == "live"
    assert kept.openai_api_key is not None
