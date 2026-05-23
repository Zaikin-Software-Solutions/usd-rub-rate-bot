from __future__ import annotations

import re

import aiohttp
import pytest
from aioresponses import aioresponses

from usd_rub_rate_bot.adapters.akbars import API_URL, AkBarsClient
from usd_rub_rate_bot.adapters.base import RateSourceError

URL_RE = re.compile(re.escape(API_URL) + r".*")


@pytest.fixture
async def session() -> aiohttp.ClientSession:  # type: ignore[misc]
    s = aiohttp.ClientSession()
    try:
        yield s
    finally:
        await s.close()


async def test_parses_buy_and_sell(session: aiohttp.ClientSession) -> None:
    payload = {"branches": [{"buyPrice": 89.10, "sellPrice": 92.40}]}
    with aioresponses() as m:
        m.get(URL_RE, payload=payload)
        client = AkBarsClient(session, city_fias_ref="city-x")
        rate = await client.fetch_rate()
    assert rate.source == "AkBars"
    assert rate.buy == 89.10
    assert rate.sell == 92.40


async def test_empty_branches_raises(session: aiohttp.ClientSession) -> None:
    with aioresponses() as m:
        m.get(URL_RE, payload={"branches": []})
        client = AkBarsClient(session, city_fias_ref="city-x")
        with pytest.raises(RateSourceError):
            await client.fetch_rate()


async def test_missing_buy_raises(session: aiohttp.ClientSession) -> None:
    with aioresponses() as m:
        m.get(URL_RE, payload={"branches": [{"sellPrice": 92.40}]})
        client = AkBarsClient(session, city_fias_ref="city-x")
        with pytest.raises(RateSourceError):
            await client.fetch_rate()


async def test_zero_sell_raises(session: aiohttp.ClientSession) -> None:
    with aioresponses() as m:
        m.get(URL_RE, payload={"branches": [{"buyPrice": 89.0, "sellPrice": 0}]})
        client = AkBarsClient(session, city_fias_ref="city-x")
        with pytest.raises(RateSourceError):
            await client.fetch_rate()


async def test_http_500_raises(session: aiohttp.ClientSession) -> None:
    with aioresponses() as m:
        m.get(URL_RE, status=500, body="boom")
        client = AkBarsClient(session, city_fias_ref="city-x")
        with pytest.raises(RateSourceError):
            await client.fetch_rate()
