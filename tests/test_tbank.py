from __future__ import annotations

import re

import aiohttp
import pytest
from aioresponses import aioresponses

from usd_rub_rate_bot.adapters.base import RateSourceError
from usd_rub_rate_bot.adapters.tbank import API_URL, TBankClient

URL_RE = re.compile(re.escape(API_URL) + r".*")


@pytest.fixture
async def session() -> aiohttp.ClientSession:  # type: ignore[misc]
    s = aiohttp.ClientSession()
    try:
        yield s
    finally:
        await s.close()


def _ok_payload(rates: list[dict[str, object]]) -> dict[str, object]:
    return {"resultCode": "OK", "payload": {"rates": rates}}


async def test_picks_configured_category(session: aiohttp.ClientSession) -> None:
    payload = _ok_payload(
        [
            {"category": "DepositPayments", "buy": 80.0, "sell": 90.0},
            {"category": "ATMRateGroup", "buy": 88.95, "sell": 92.10},
        ]
    )
    with aioresponses() as m:
        m.get(URL_RE, payload=payload)
        client = TBankClient(session, category="ATMRateGroup")
        rate = await client.fetch_rate()
    assert rate.source == "T-Bank"
    assert rate.buy == 88.95
    assert rate.sell == 92.10


async def test_missing_category_raises(session: aiohttp.ClientSession) -> None:
    payload = _ok_payload([{"category": "DepositPayments", "buy": 80.0, "sell": 90.0}])
    with aioresponses() as m:
        m.get(URL_RE, payload=payload)
        client = TBankClient(session, category="ATMRateGroup")
        with pytest.raises(RateSourceError):
            await client.fetch_rate()


async def test_non_ok_result_code_raises(session: aiohttp.ClientSession) -> None:
    with aioresponses() as m:
        m.get(URL_RE, payload={"resultCode": "FAIL", "payload": {"rates": []}})
        client = TBankClient(session, category="ATMRateGroup")
        with pytest.raises(RateSourceError):
            await client.fetch_rate()


async def test_invalid_buy_sell_raises(session: aiohttp.ClientSession) -> None:
    payload = _ok_payload([{"category": "ATMRateGroup", "buy": 0, "sell": 92.10}])
    with aioresponses() as m:
        m.get(URL_RE, payload=payload)
        client = TBankClient(session, category="ATMRateGroup")
        with pytest.raises(RateSourceError):
            await client.fetch_rate()


async def test_http_502_raises(session: aiohttp.ClientSession) -> None:
    with aioresponses() as m:
        m.get(URL_RE, status=502, body="bad gateway")
        client = TBankClient(session, category="ATMRateGroup")
        with pytest.raises(RateSourceError):
            await client.fetch_rate()
