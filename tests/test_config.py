from __future__ import annotations

import pytest
from pydantic import ValidationError

from usd_rub_rate_bot.config import (
    DEFAULT_AKBARS_CITY_FIAS_REF,
    DEFAULT_TBANK_RATE_CATEGORY,
    Settings,
)


def _base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "-1001")


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.tbank_rate_category == DEFAULT_TBANK_RATE_CATEGORY
    assert settings.akbars_city_fias_ref == DEFAULT_AKBARS_CITY_FIAS_REF
    assert settings.publish_cron == "* * * * *"
    assert settings.log_level == "INFO"


def test_tbank_category_overridable(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("TBANK_RATE_CATEGORY", "ATMRateGroup")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.tbank_rate_category == "ATMRateGroup"


def test_missing_token_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "-1001")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_timeout_must_be_positive(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("HTTP_TIMEOUT_SECONDS", "0")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]
