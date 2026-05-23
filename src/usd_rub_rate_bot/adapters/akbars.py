"""AkBars bank cash USD rate adapter.

Endpoint: https://www.akbars.ru/api/v2/offices/bestrates
Returns the "best" buy/sell rates across the bank's branches in a given city.
"""

from __future__ import annotations

from typing import Any

import aiohttp

from usd_rub_rate_bot.adapters.base import RateSourceError, fetch_json
from usd_rub_rate_bot.domain.models import CommercialRate

API_URL = "https://www.akbars.ru/api/v2/offices/bestrates"
SOURCE = "AkBars"


class AkBarsClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        city_fias_ref: str,
        timeout_seconds: float = 10.0,
        api_url: str = API_URL,
    ) -> None:
        self._session = session
        self._city_fias_ref = city_fias_ref
        self._timeout = timeout_seconds
        self._api_url = api_url

    async def fetch_rate(self) -> CommercialRate:
        params = f"?cityFiasRef={self._city_fias_ref}&currencycode=USD"
        # AkBars sometimes rejects "default" UAs; mimic a real browser.
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0 Safari/537.36"
            ),
            "Accept": "application/json",
        }
        data = await fetch_json(
            self._session,
            self._api_url + params,
            timeout_seconds=self._timeout,
            headers=headers,
        )
        return _parse_response(data)


def _parse_response(data: Any) -> CommercialRate:
    if not isinstance(data, dict):
        raise RateSourceError(f"AkBars: expected object, got {type(data).__name__}")

    branches = data.get("branches")
    if not isinstance(branches, list) or not branches:
        raise RateSourceError("AkBars: 'branches' is missing or empty")

    branch = branches[0]
    if not isinstance(branch, dict):
        raise RateSourceError("AkBars: first branch is not an object")

    buy = _positive_float(branch.get("buyPrice"))
    sell = _positive_float(branch.get("sellPrice"))

    if buy is None:
        raise RateSourceError(f"AkBars: invalid buyPrice {branch.get('buyPrice')!r}")
    if sell is None:
        raise RateSourceError(f"AkBars: invalid sellPrice {branch.get('sellPrice')!r}")

    return CommercialRate(source=SOURCE, buy=buy, sell=sell)


def _positive_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    return None
