from __future__ import annotations

import pytest

from usd_rub_rate_bot.adapters.base import RateSourceError
from usd_rub_rate_bot.domain.models import CentralBankRate
from usd_rub_rate_bot.services.cbr_provider import CentralBankProvider


class _StubClient:
    def __init__(self, source: str, result: CentralBankRate | Exception) -> None:
        self.source = source
        self._result = result
        self.calls = 0

    async def fetch_rate(self) -> CentralBankRate:
        self.calls += 1
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


async def test_first_success_wins() -> None:
    primary = _StubClient("primary", CentralBankRate(source="primary", value=90.0))
    fallback = _StubClient("fallback", CentralBankRate(source="fallback", value=91.0))
    provider = CentralBankProvider((primary, fallback))

    rate = await provider.fetch_rate()

    assert rate is not None
    assert rate.value == 90.0
    assert primary.calls == 1
    assert fallback.calls == 0


async def test_falls_back_when_primary_fails() -> None:
    primary = _StubClient("primary", RateSourceError("down"))
    fallback = _StubClient("fallback", CentralBankRate(source="fallback", value=91.0))
    provider = CentralBankProvider((primary, fallback))

    rate = await provider.fetch_rate()

    assert rate is not None
    assert rate.value == 91.0
    assert primary.calls == 1
    assert fallback.calls == 1


async def test_returns_none_when_all_fail() -> None:
    primary = _StubClient("primary", RateSourceError("down"))
    fallback = _StubClient("fallback", RateSourceError("also down"))
    provider = CentralBankProvider((primary, fallback))

    rate = await provider.fetch_rate()

    assert rate is None


async def test_unexpected_exception_is_treated_as_failure() -> None:
    primary = _StubClient("primary", RuntimeError("boom"))
    fallback = _StubClient("fallback", CentralBankRate(source="fallback", value=91.0))
    provider = CentralBankProvider((primary, fallback))

    rate = await provider.fetch_rate()

    assert rate is not None
    assert rate.value == 91.0


async def test_empty_clients_rejected() -> None:
    with pytest.raises(ValueError, match="at least one"):
        CentralBankProvider(())
