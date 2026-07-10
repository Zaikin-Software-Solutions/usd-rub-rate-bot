"""AkBars bank cash USD rate adapter.

Endpoint: https://www.akbars.ru/api/currency-svc/offices/best-rates
Returns the "best" buy/sell rates across the bank's branches in a given city
as a flat list of per-currency quotes.
"""

from __future__ import annotations

from typing import Any

import aiohttp

from usd_rub_rate_bot.adapters.base import RateSourceError, fetch_json
from usd_rub_rate_bot.domain.models import CommercialRate

API_URL = "https://www.akbars.ru/api/currency-svc/offices/best-rates"
SOURCE = "AkBars"
CURRENCY_CODE = "USD"


class AkBarsClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        city_fias_ref: str,
        timeout_seconds: float = 10.0,
        api_url: str = API_URL,
        proxy_url: str | None = None,
    ) -> None:
        self._session = session
        self._city_fias_ref = city_fias_ref
        self._timeout = timeout_seconds
        self._api_url = api_url
        self._proxy_url = proxy_url

    async def fetch_rate(self) -> CommercialRate:
        params = f"?cityFiasRef={self._city_fias_ref}"
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
            proxy=self._proxy_url,
        )
        return _parse_response(data)


def _parse_response(data: Any) -> CommercialRate:
    if not isinstance(data, list) or not data:
        raise RateSourceError("AkBars: expected a non-empty list of quotes")

    quote = _find_usd_quote(data)
    if quote is None:
        raise RateSourceError(f"AkBars: {CURRENCY_CODE} quote not found in response")

    # ``purchasePrice`` is the rate at which the bank buys USD from the customer,
    # ``salePrice`` the rate at which it sells USD to the customer.
    buy = _positive_float(quote.get("purchasePrice"))
    sell = _positive_float(quote.get("salePrice"))

    if buy is None:
        raise RateSourceError(f"AkBars: invalid purchasePrice {quote.get('purchasePrice')!r}")
    if sell is None:
        raise RateSourceError(f"AkBars: invalid salePrice {quote.get('salePrice')!r}")

    return CommercialRate(source=SOURCE, buy=buy, sell=sell)


def _find_usd_quote(quotes: list[Any]) -> dict[str, Any] | None:
    for quote in quotes:
        if isinstance(quote, dict) and quote.get("currencyCode") == CURRENCY_CODE:
            return quote
    return None


def _positive_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    return None
