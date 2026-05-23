"""Concurrent rate collection from all sources."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol

from usd_rub_rate_bot.adapters.base import RateSourceError
from usd_rub_rate_bot.domain.models import CentralBankRate, CommercialRate
from usd_rub_rate_bot.logger import get_logger
from usd_rub_rate_bot.services.cbr_provider import CentralBankProvider

log = get_logger(__name__)


class _CommercialClient(Protocol):
    async def fetch_rate(self) -> CommercialRate: ...


@dataclass(frozen=True)
class RatesReport:
    """Snapshot of one round of rate fetching.

    Any field can be ``None`` when the corresponding source was unreachable.
    The publisher renders ``n/a`` for missing values rather than fabricating zeros.
    """

    akbars: CommercialRate | None
    tbank: CommercialRate | None
    cbr: CentralBankRate | None

    def has_any(self) -> bool:
        return self.akbars is not None or self.tbank is not None or self.cbr is not None


class RatesAggregator:
    """Fetches all sources concurrently and returns a ``RatesReport``."""

    def __init__(
        self,
        *,
        akbars: _CommercialClient,
        tbank: _CommercialClient,
        cbr_provider: CentralBankProvider,
    ) -> None:
        self._akbars = akbars
        self._tbank = tbank
        self._cbr_provider = cbr_provider

    async def collect(self) -> RatesReport:
        akbars_task = asyncio.create_task(self._safe_commercial(self._akbars, "AkBars"))
        tbank_task = asyncio.create_task(self._safe_commercial(self._tbank, "T-Bank"))
        cbr_task = asyncio.create_task(self._safe_cbr())
        akbars, tbank, cbr = await asyncio.gather(akbars_task, tbank_task, cbr_task)
        return RatesReport(akbars=akbars, tbank=tbank, cbr=cbr)

    @staticmethod
    async def _safe_commercial(
        client: _CommercialClient, source_name: str
    ) -> CommercialRate | None:
        try:
            return await client.fetch_rate()
        except RateSourceError as exc:
            log.warning("commercial_source_failed", source=source_name, error=str(exc))
            return None
        except Exception:
            log.exception("commercial_source_unexpected_error", source=source_name)
            return None

    async def _safe_cbr(self) -> CentralBankRate | None:
        try:
            return await self._cbr_provider.fetch_rate()
        except Exception:
            log.exception("cbr_provider_unexpected_error")
            return None
