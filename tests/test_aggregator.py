from __future__ import annotations

from usd_rub_rate_bot.adapters.base import RateSourceError
from usd_rub_rate_bot.domain.models import CentralBankRate, CommercialRate
from usd_rub_rate_bot.services.aggregator import RatesAggregator
from usd_rub_rate_bot.services.cbr_provider import CentralBankProvider


class _CommercialStub:
    def __init__(self, result: CommercialRate | Exception) -> None:
        self._result = result

    async def fetch_rate(self) -> CommercialRate:
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class _CbrStub:
    source = "stub"

    def __init__(self, result: CentralBankRate | Exception) -> None:
        self._result = result

    async def fetch_rate(self) -> CentralBankRate:
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


def _aggregator(
    akbars: CommercialRate | Exception,
    tbank: CommercialRate | Exception,
    cbr: CentralBankRate | Exception,
) -> RatesAggregator:
    return RatesAggregator(
        akbars=_CommercialStub(akbars),
        tbank=_CommercialStub(tbank),
        cbr_provider=CentralBankProvider((_CbrStub(cbr),)),
    )


async def test_all_succeed() -> None:
    aggregator = _aggregator(
        akbars=CommercialRate(source="AkBars", buy=89.0, sell=92.0),
        tbank=CommercialRate(source="T-Bank", buy=88.0, sell=91.5),
        cbr=CentralBankRate(source="cbr", value=90.0),
    )
    report = await aggregator.collect()
    assert report.akbars is not None
    assert report.tbank is not None
    assert report.cbr is not None
    assert report.has_any()


async def test_partial_success_one_source_down() -> None:
    aggregator = _aggregator(
        akbars=RateSourceError("akbars down"),
        tbank=CommercialRate(source="T-Bank", buy=88.0, sell=91.5),
        cbr=CentralBankRate(source="cbr", value=90.0),
    )
    report = await aggregator.collect()
    assert report.akbars is None
    assert report.tbank is not None
    assert report.cbr is not None


async def test_unexpected_exception_isolated_to_one_source() -> None:
    aggregator = _aggregator(
        akbars=RuntimeError("boom"),
        tbank=CommercialRate(source="T-Bank", buy=88.0, sell=91.5),
        cbr=CentralBankRate(source="cbr", value=90.0),
    )
    report = await aggregator.collect()
    assert report.akbars is None
    assert report.tbank is not None


async def test_all_fail_has_any_false() -> None:
    aggregator = _aggregator(
        akbars=RateSourceError("down"),
        tbank=RateSourceError("down"),
        cbr=RateSourceError("down"),
    )
    report = await aggregator.collect()
    assert report.akbars is None
    assert report.tbank is None
    assert report.cbr is None
    assert not report.has_any()
