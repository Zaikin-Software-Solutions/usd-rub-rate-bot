"""High-level publish flow: collect rates → format → send to Telegram."""

from __future__ import annotations

from aiogram import Bot

from usd_rub_rate_bot.logger import get_logger
from usd_rub_rate_bot.services.aggregator import RatesAggregator
from usd_rub_rate_bot.services.message_builder import build_message

log = get_logger(__name__)


class RatesPublisher:
    """Orchestrates a single publish iteration."""

    def __init__(
        self,
        *,
        aggregator: RatesAggregator,
        bot: Bot,
        channel_id: str,
    ) -> None:
        self._aggregator = aggregator
        self._bot = bot
        self._channel_id = channel_id

    async def publish_once(self) -> None:
        report = await self._aggregator.collect()
        message = build_message(report)
        if not message:
            log.warning("publish_skipped_all_sources_failed")
            return

        try:
            await self._bot.send_message(chat_id=self._channel_id, text=message)
        except Exception:
            log.exception("telegram_send_failed", channel_id=self._channel_id)
            return

        log.info(
            "published",
            channel_id=self._channel_id,
            akbars=report.akbars is not None,
            tbank=report.tbank is not None,
            cbr=report.cbr.source if report.cbr else None,
        )
