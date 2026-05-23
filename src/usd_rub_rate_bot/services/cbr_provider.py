"""Aggregating provider for the Central Bank rate with fallback across sources."""

from __future__ import annotations

from typing import Protocol

from usd_rub_rate_bot.adapters.base import RateSourceError
from usd_rub_rate_bot.domain.models import CentralBankRate
from usd_rub_rate_bot.logger import get_logger

log = get_logger(__name__)


class _CbrClient(Protocol):
    source: str

    async def fetch_rate(self) -> CentralBankRate: ...


class CentralBankProvider:
    """Try several CBR sources in order, return the first that succeeds."""

    def __init__(self, clients: tuple[_CbrClient, ...]) -> None:
        if not clients:
            raise ValueError("CentralBankProvider requires at least one client")
        self._clients = clients

    async def fetch_rate(self) -> CentralBankRate | None:
        for client in self._clients:
            try:
                return await client.fetch_rate()
            except RateSourceError as exc:
                log.warning("cbr_source_failed", source=client.source, error=str(exc))
            except Exception:
                log.exception("cbr_source_unexpected_error", source=client.source)
        return None
