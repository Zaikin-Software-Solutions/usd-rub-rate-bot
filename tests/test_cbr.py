from __future__ import annotations

import re

import aiohttp
import pytest
from aioresponses import aioresponses

from usd_rub_rate_bot.adapters.base import RateSourceError
from usd_rub_rate_bot.adapters.cbr import (
    CBR_OFFICIAL_XML_URL,
    CBR_XML_DAILY_URL,
    CbrOfficialClient,
    CbrXmlDailyClient,
)

XML_DAILY_RE = re.compile(re.escape(CBR_XML_DAILY_URL) + r".*")
OFFICIAL_RE = re.compile(re.escape(CBR_OFFICIAL_XML_URL) + r".*")


@pytest.fixture
async def session() -> aiohttp.ClientSession:  # type: ignore[misc]
    s = aiohttp.ClientSession()
    try:
        yield s
    finally:
        await s.close()


# -- cbr-xml-daily.ru ----------------------------------------------------------


async def test_xml_daily_parses_usd(session: aiohttp.ClientSession) -> None:
    payload = {"Valute": {"USD": {"Value": 90.25}}}
    with aioresponses() as m:
        m.get(XML_DAILY_RE, payload=payload)
        client = CbrXmlDailyClient(session)
        rate = await client.fetch_rate()
    assert rate.value == 90.25
    assert "xml-daily" in rate.source


async def test_xml_daily_missing_usd_raises(session: aiohttp.ClientSession) -> None:
    with aioresponses() as m:
        m.get(XML_DAILY_RE, payload={"Valute": {}})
        client = CbrXmlDailyClient(session)
        with pytest.raises(RateSourceError):
            await client.fetch_rate()


async def test_xml_daily_negative_value_raises(session: aiohttp.ClientSession) -> None:
    with aioresponses() as m:
        m.get(XML_DAILY_RE, payload={"Valute": {"USD": {"Value": -1}}})
        client = CbrXmlDailyClient(session)
        with pytest.raises(RateSourceError):
            await client.fetch_rate()


# -- www.cbr.ru official XML ---------------------------------------------------


_XML_BODY = """<?xml version="1.0" encoding="windows-1251"?>
<ValCurs Date="22.05.2026" name="Foreign Currency Market">
  <Valute ID="R01010">
    <NumCode>036</NumCode>
    <CharCode>AUD</CharCode>
    <Nominal>1</Nominal>
    <Name>Australian dollar</Name>
    <Value>58,1234</Value>
  </Valute>
  <Valute ID="R01235">
    <NumCode>840</NumCode>
    <CharCode>USD</CharCode>
    <Nominal>1</Nominal>
    <Name>US dollar</Name>
    <Value>90,2500</Value>
  </Valute>
</ValCurs>
"""


async def test_official_xml_parses_usd(session: aiohttp.ClientSession) -> None:
    with aioresponses() as m:
        m.get(OFFICIAL_RE, body=_XML_BODY, content_type="application/xml")
        client = CbrOfficialClient(session)
        rate = await client.fetch_rate()
    assert rate.value == pytest.approx(90.25)


async def test_official_xml_with_nominal_normalises(
    session: aiohttp.ClientSession,
) -> None:
    body = """<?xml version="1.0" encoding="utf-8"?>
<ValCurs>
  <Valute>
    <CharCode>USD</CharCode>
    <Nominal>10</Nominal>
    <Value>902,5</Value>
  </Valute>
</ValCurs>
"""
    with aioresponses() as m:
        m.get(OFFICIAL_RE, body=body, content_type="application/xml")
        client = CbrOfficialClient(session)
        rate = await client.fetch_rate()
    assert rate.value == pytest.approx(90.25)


async def test_official_xml_without_usd_raises(session: aiohttp.ClientSession) -> None:
    body = """<?xml version="1.0"?><ValCurs></ValCurs>"""
    with aioresponses() as m:
        m.get(OFFICIAL_RE, body=body, content_type="application/xml")
        client = CbrOfficialClient(session)
        with pytest.raises(RateSourceError):
            await client.fetch_rate()


async def test_official_xml_garbage_raises(session: aiohttp.ClientSession) -> None:
    with aioresponses() as m:
        m.get(OFFICIAL_RE, body="not xml", content_type="text/plain")
        client = CbrOfficialClient(session)
        with pytest.raises(RateSourceError):
            await client.fetch_rate()
