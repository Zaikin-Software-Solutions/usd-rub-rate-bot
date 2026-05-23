"""Entry point: wire everything together and run the scheduler."""

from __future__ import annotations

import asyncio
import signal

import aiohttp
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from usd_rub_rate_bot.adapters.akbars import AkBarsClient
from usd_rub_rate_bot.adapters.cbr import CbrOfficialClient, CbrXmlDailyClient
from usd_rub_rate_bot.adapters.tbank import TBankClient
from usd_rub_rate_bot.config import Settings
from usd_rub_rate_bot.logger import configure_logging, get_logger
from usd_rub_rate_bot.scheduler import build_scheduler
from usd_rub_rate_bot.services.aggregator import RatesAggregator
from usd_rub_rate_bot.services.cbr_provider import CentralBankProvider
from usd_rub_rate_bot.services.publisher import RatesPublisher


async def _run(settings: Settings) -> None:
    log = get_logger(__name__)
    log.info(
        "starting",
        cron=settings.publish_cron,
        channel_id=settings.telegram_channel_id,
        tbank_category=settings.tbank_rate_category,
    )

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=None),
    )
    http_session = aiohttp.ClientSession()
    try:
        proxy = settings.http_proxy_url
        akbars = AkBarsClient(
            http_session,
            city_fias_ref=settings.akbars_city_fias_ref,
            timeout_seconds=settings.http_timeout_seconds,
            proxy_url=proxy,
        )
        tbank = TBankClient(
            http_session,
            category=settings.tbank_rate_category,
            timeout_seconds=settings.http_timeout_seconds,
            proxy_url=proxy,
        )
        cbr_provider = CentralBankProvider(
            clients=(
                CbrXmlDailyClient(
                    http_session,
                    timeout_seconds=settings.http_timeout_seconds,
                    proxy_url=proxy,
                ),
                CbrOfficialClient(
                    http_session,
                    timeout_seconds=settings.http_timeout_seconds,
                    proxy_url=proxy,
                ),
            )
        )
        aggregator = RatesAggregator(akbars=akbars, tbank=tbank, cbr_provider=cbr_provider)
        publisher = RatesPublisher(
            aggregator=aggregator,
            bot=bot,
            channel_id=settings.telegram_channel_id,
        )

        scheduler = build_scheduler(publisher.publish_once, settings.publish_cron)
        scheduler.start()

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop.set)
            except NotImplementedError:
                pass

        log.info("ready")
        await stop.wait()
        log.info("shutting_down")
        scheduler.shutdown(wait=False)
    finally:
        await http_session.close()
        await bot.session.close()


def main() -> None:
    settings = Settings()  # type: ignore[call-arg]  # values come from env / .env
    configure_logging(level=settings.log_level, fmt=settings.log_format)
    try:
        asyncio.run(_run(settings))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
