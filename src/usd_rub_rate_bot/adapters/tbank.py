"""T-Bank cash USD rate adapter.

Endpoint: https://api.tinkoff.ru/v1/currency_rates?from=USD&to=RUB

The endpoint returns multiple categories; we pick one (configurable, defaults to
``ATMRateGroup`` — the rate T-Bank uses at its ATMs, which is the closest
publicly available proxy for a "cash" rate).
"""

from __future__ import annotations

from typing import Any

import aiohttp

from usd_rub_rate_bot.adapters.base import RateSourceError, fetch_json
from usd_rub_rate_bot.domain.models import CommercialRate

API_URL = "https://api.tinkoff.ru/v1/currency_rates"
SOURCE = "T-Bank"


class TBankClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        category: str,
        timeout_seconds: float = 10.0,
        api_url: str = API_URL,
        proxy_url: str | None = None,
    ) -> None:
        self._session = session
        self._category = category
        self._timeout = timeout_seconds
        self._api_url = api_url
        self._proxy_url = proxy_url

    async def fetch_rate(self) -> CommercialRate:
        url = f"{self._api_url}?from=USD&to=RUB"
        data = await fetch_json(
            self._session,
            url,
            timeout_seconds=self._timeout,
            proxy=self._proxy_url,
        )
        return _parse_response(data, category=self._category)


def _parse_response(data: Any, *, category: str) -> CommercialRate:
    if not isinstance(data, dict):
        raise RateSourceError(f"T-Bank: expected object, got {type(data).__name__}")

    if data.get("resultCode") != "OK":
        raise RateSourceError(f"T-Bank: resultCode={data.get('resultCode')!r}")

    payload = data.get("payload")
    if not isinstance(payload, dict):
        raise RateSourceError("T-Bank: 'payload' is missing")

    rates = payload.get("rates")
    if not isinstance(rates, list):
        raise RateSourceError("T-Bank: 'rates' is not a list")

    for item in rates:
        if not isinstance(item, dict):
            continue
        if item.get("category") != category:
            continue
        raw_buy = item.get("buy")
        raw_sell = item.get("sell")
        buy = _positive_float(raw_buy)
        sell = _positive_float(raw_sell)
        if buy is None or sell is None:
            raise RateSourceError(
                f"T-Bank: invalid buy/sell for category {category}: {raw_buy!r}/{raw_sell!r}"
            )
        return CommercialRate(source=SOURCE, buy=buy, sell=sell)

    available = sorted(
        {
            cat
            for item in rates
            if isinstance(item, dict)
            for cat in [item.get("category")]
            if isinstance(cat, str)
        }
    )
    raise RateSourceError(f"T-Bank: category {category!r} not found; available: {available[:10]}")


def _positive_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    return None
