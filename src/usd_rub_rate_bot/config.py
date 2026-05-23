"""Application configuration loaded from environment variables."""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Kazan FIAS reference — historical default for the AkBars endpoint.
DEFAULT_AKBARS_CITY_FIAS_REF = "6b1bab7d-ee45-4168-a2a6-4ce2880d90d3"

# ATMCashoutRateGroup is the T-Bank rate used for cash withdrawal/exchange at ATMs.
# It matches the rate described on https://www.tbank.ru/finance/blog/atm-exchange/
# as the rate shown to the customer on the ATM screen before confirming the exchange.
DEFAULT_TBANK_RATE_CATEGORY = "ATMCashoutRateGroup"


class Settings(BaseSettings):
    """Runtime configuration.

    All values are loaded from environment variables (or a local .env file in dev).
    Names mirror those documented in .env.example.
    """

    telegram_bot_token: str = Field(min_length=1)
    telegram_channel_id: str = Field(min_length=1)

    publish_cron: str = "* * * * *"
    http_timeout_seconds: float = Field(default=10.0, gt=0, le=60)

    tbank_rate_category: str = DEFAULT_TBANK_RATE_CATEGORY
    akbars_city_fias_ref: str = DEFAULT_AKBARS_CITY_FIAS_REF

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
