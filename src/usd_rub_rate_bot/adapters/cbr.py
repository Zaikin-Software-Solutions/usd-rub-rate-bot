"""Central Bank of Russia (CBR) USD rate adapters.

Two independent sources are queried in order; the first one that succeeds wins:

1. cbr-xml-daily.ru — a popular community JSON mirror, fast and CDN-friendly.
2. www.cbr.ru — the official XML daily quotes endpoint.

Each adapter is a standalone class; the caller (``CentralBankProvider``) orchestrates
fallback between them.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import aiohttp

from usd_rub_rate_bot.adapters.base import RateSourceError, fetch_json, fetch_text
from usd_rub_rate_bot.domain.models import CentralBankRate

CBR_XML_DAILY_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
CBR_OFFICIAL_XML_URL = "https://www.cbr.ru/scripts/XML_daily.asp"


class CbrXmlDailyClient:
    """Source 1: cbr-xml-daily.ru — JSON mirror."""

    source = "CBR (xml-daily)"

    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        timeout_seconds: float = 10.0,
        api_url: str = CBR_XML_DAILY_URL,
    ) -> None:
        self._session = session
        self._timeout = timeout_seconds
        self._api_url = api_url

    async def fetch_rate(self) -> CentralBankRate:
        data = await fetch_json(self._session, self._api_url, timeout_seconds=self._timeout)
        return _parse_xml_daily(data, source=self.source)


class CbrOfficialClient:
    """Source 2: www.cbr.ru — official XML."""

    source = "CBR (cbr.ru)"

    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        timeout_seconds: float = 10.0,
        api_url: str = CBR_OFFICIAL_XML_URL,
    ) -> None:
        self._session = session
        self._timeout = timeout_seconds
        self._api_url = api_url

    async def fetch_rate(self) -> CentralBankRate:
        body = await fetch_text(self._session, self._api_url, timeout_seconds=self._timeout)
        return _parse_official_xml(body, source=self.source)


def _parse_xml_daily(data: Any, *, source: str) -> CentralBankRate:
    if not isinstance(data, dict):
        raise RateSourceError(f"{source}: expected object, got {type(data).__name__}")
    valute = data.get("Valute")
    if not isinstance(valute, dict):
        raise RateSourceError(f"{source}: 'Valute' missing")
    usd = valute.get("USD")
    if not isinstance(usd, dict):
        raise RateSourceError(f"{source}: 'Valute.USD' missing")
    raw_value = usd.get("Value")
    value = _positive_float(raw_value)
    if value is None:
        raise RateSourceError(f"{source}: invalid 'Value' {raw_value!r}")
    return CentralBankRate(source=source, value=value)


def _parse_official_xml(body: str, *, source: str) -> CentralBankRate:
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise RateSourceError(f"{source}: XML parse error: {exc}") from exc

    for valute in root.findall("Valute"):
        char_code = valute.findtext("CharCode")
        if char_code != "USD":
            continue
        nominal_text = valute.findtext("Nominal") or "1"
        value_text = valute.findtext("Value") or ""
        try:
            nominal = float(nominal_text.replace(",", "."))
            value = float(value_text.replace(",", "."))
        except ValueError as exc:
            raise RateSourceError(
                f"{source}: cannot parse nominal/value {nominal_text!r}/{value_text!r}"
            ) from exc
        if nominal <= 0 or value <= 0:
            raise RateSourceError(f"{source}: non-positive nominal/value {nominal}/{value}")
        return CentralBankRate(source=source, value=value / nominal)

    raise RateSourceError(f"{source}: USD not found in XML")


def _positive_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    return None
