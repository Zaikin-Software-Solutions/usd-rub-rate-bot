from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from usd_rub_rate_bot.domain.models import CentralBankRate, CommercialRate
from usd_rub_rate_bot.services.aggregator import RatesReport
from usd_rub_rate_bot.services.publisher import RatesPublisher


class _AggregatorStub:
    def __init__(self, report: RatesReport) -> None:
        self._report = report

    async def collect(self) -> RatesReport:
        return self._report


def _pub(aggregator: Any, bot: Any) -> RatesPublisher:
    return RatesPublisher(aggregator=aggregator, bot=bot, channel_id="-1001")


@pytest.mark.asyncio
async def test_happy_path_sends_message() -> None:
    report = RatesReport(
        akbars=CommercialRate(source="AkBars", buy=89.1, sell=92.4),
        tbank=CommercialRate(source="T-Bank", buy=88.95, sell=92.1),
        cbr=CentralBankRate(source="CBR (xml-daily)", value=90.25),
    )
    bot = AsyncMock()
    pub = _pub(_AggregatorStub(report), bot)

    await pub.publish_once()

    bot.send_message.assert_awaited_once()
    sent_text = bot.send_message.await_args.kwargs["text"]
    assert "AkBars" in sent_text and "T-Bank" in sent_text and "ЦБ РФ" in sent_text


@pytest.mark.asyncio
async def test_all_sources_failed_skips_send() -> None:
    bot = AsyncMock()
    pub = _pub(
        _AggregatorStub(RatesReport(akbars=None, tbank=None, cbr=None)),
        bot,
    )

    await pub.publish_once()

    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_partial_failure_still_sends() -> None:
    report = RatesReport(
        akbars=None,
        tbank=CommercialRate(source="T-Bank", buy=88.95, sell=92.1),
        cbr=None,
    )
    bot = AsyncMock()
    pub = _pub(_AggregatorStub(report), bot)

    await pub.publish_once()

    bot.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_telegram_error_swallowed() -> None:
    report = RatesReport(
        akbars=CommercialRate(source="AkBars", buy=89.1, sell=92.4),
        tbank=None,
        cbr=None,
    )
    bot = AsyncMock()
    bot.send_message.side_effect = RuntimeError("tg 502")
    pub = _pub(_AggregatorStub(report), bot)

    await pub.publish_once()  # must not raise
    bot.send_message.assert_awaited_once()
