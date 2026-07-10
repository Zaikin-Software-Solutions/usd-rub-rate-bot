from __future__ import annotations

import re

import aiohttp
import pytest
from aioresponses import aioresponses

from usd_rub_rate_bot.adapters.akbars import API_URL, AkBarsClient
from usd_rub_rate_bot.adapters.base import RateSourceError

URL_RE = re.compile(re.escape(API_URL) + r".*")


def _payload(*, purchase: float | None = 89.10, sale: float | None = 92.40) -> list[dict]:
    usd: dict[str, object] = {"currencyCode": "USD", "isCash": True}
    if purchase is not None:
        usd["purchasePrice"] = purchase
    if sale is not None:
        usd["salePrice"] = sale
    return [
        {"currencyCode": "EUR", "purchasePrice": 90.2, "salePrice": 92.3, "isCash": True},
        usd,
        {"currencyCode": "CNY", "purchasePrice": 11.1, "salePrice": 11.63, "isCash": True},
    ]


@pytest.fixture
async def session() -> aiohttp.ClientSession:  # type: ignore[misc]
    s = aiohttp.ClientSession()
    try:
        yield s
    finally:
        await s.close()


async def test_parses_buy_and_sell(session: aiohttp.ClientSession) -> None:
    with aioresponses() as m:
        m.get(URL_RE, payload=_payload())
        client = AkBarsClient(session, city_fias_ref="city-x")
        rate = await client.fetch_rate()
    assert rate.source == "AkBars"
    # purchasePrice -> buy, salePrice -> sell
    assert rate.buy == 89.10
    assert rate.sell == 92.40


async def test_empty_list_raises(session: aiohttp.ClientSession) -> None:
    with aioresponses() as m:
        m.get(URL_RE, payload=[])
        client = AkBarsClient(session, city_fias_ref="city-x")
        with pytest.raises(RateSourceError):
            await client.fetch_rate()


async def test_missing_usd_raises(session: aiohttp.ClientSession) -> None:
    with aioresponses() as m:
        m.get(URL_RE, payload=[{"currencyCode": "EUR", "purchasePrice": 90.2, "salePrice": 92.3}])
        client = AkBarsClient(session, city_fias_ref="city-x")
        with pytest.raises(RateSourceError):
            await client.fetch_rate()


async def test_missing_buy_raises(session: aiohttp.ClientSession) -> None:
    with aioresponses() as m:
        m.get(URL_RE, payload=_payload(purchase=None))
        client = AkBarsClient(session, city_fias_ref="city-x")
        with pytest.raises(RateSourceError):
            await client.fetch_rate()


async def test_zero_sell_raises(session: aiohttp.ClientSession) -> None:
    with aioresponses() as m:
        m.get(URL_RE, payload=_payload(sale=0))
        client = AkBarsClient(session, city_fias_ref="city-x")
        with pytest.raises(RateSourceError):
            await client.fetch_rate()


async def test_http_500_raises(session: aiohttp.ClientSession) -> None:
    with aioresponses() as m:
        m.get(URL_RE, status=500, body="boom")
        client = AkBarsClient(session, city_fias_ref="city-x")
        with pytest.raises(RateSourceError):
            await client.fetch_rate()


async def test_proxy_url_is_forwarded(session: aiohttp.ClientSession) -> None:
    with aioresponses() as m:
        m.get(URL_RE, payload=_payload())
        client = AkBarsClient(
            session,
            city_fias_ref="city-x",
            proxy_url="http://user:pass@proxy.example:1234",
        )
        await client.fetch_rate()

        ((_key, calls),) = list(m.requests.items())
        assert calls[0].kwargs.get("proxy") == "http://user:pass@proxy.example:1234"
