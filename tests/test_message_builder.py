from __future__ import annotations

from usd_rub_rate_bot.domain.models import CentralBankRate, CommercialRate
from usd_rub_rate_bot.services.aggregator import RatesReport
from usd_rub_rate_bot.services.message_builder import build_message


def test_full_report_renders_all_lines() -> None:
    report = RatesReport(
        akbars=CommercialRate(source="AkBars", buy=73.00, sell=73.60),
        tbank=CommercialRate(source="T-Bank", buy=71.05, sell=75.70),
        cbr=CentralBankRate(source="CBR (xml-daily)", value=71.21),
    )
    msg = build_message(report)
    assert msg == (
        "AkBars (кэш): покупка 73.00 ↓ / продажа 73.60 ↑\n"
        "T-Bank (кэш): покупка 71.05 ↓ / продажа 75.70 ↑\n"
        "ЦБ РФ:  71.21\n"
        "Дифф к ЦБ (покупка): AkBars +1.79 / T-Bank −0.16\n"
        "Дифф к ЦБ (продажа): AkBars +2.39 / T-Bank +4.49"
    )


def test_missing_akbars_shows_na_and_excludes_from_diff() -> None:
    report = RatesReport(
        akbars=None,
        tbank=CommercialRate(source="T-Bank", buy=71.05, sell=75.70),
        cbr=CentralBankRate(source="CBR (xml-daily)", value=71.21),
    )
    msg = build_message(report)
    assert msg == (
        "AkBars (кэш): n/a\n"
        "T-Bank (кэш): покупка 71.05 ↓ / продажа 75.70 ↑\n"
        "ЦБ РФ:  71.21\n"
        "Дифф к ЦБ (покупка): T-Bank −0.16\n"
        "Дифф к ЦБ (продажа): T-Bank +4.49"
    )


def test_missing_cbr_drops_diff_lines() -> None:
    report = RatesReport(
        akbars=CommercialRate(source="AkBars", buy=73.00, sell=73.60),
        tbank=CommercialRate(source="T-Bank", buy=71.05, sell=75.70),
        cbr=None,
    )
    msg = build_message(report)
    assert msg == (
        "AkBars (кэш): покупка 73.00 ↓ / продажа 73.60 ↑\n"
        "T-Bank (кэш): покупка 71.05 ↓ / продажа 75.70 ↑\n"
        "ЦБ РФ:  n/a"
    )


def test_negative_diff_uses_minus_sign() -> None:
    report = RatesReport(
        akbars=CommercialRate(source="AkBars", buy=65.0, sell=68.0),
        tbank=None,
        cbr=CentralBankRate(source="CBR (xml-daily)", value=71.21),
    )
    msg = build_message(report)
    assert "AkBars −6.21" in msg  # buy diff
    assert "AkBars −3.21" in msg  # sell diff


def test_all_sources_missing_returns_empty_string() -> None:
    report = RatesReport(akbars=None, tbank=None, cbr=None)
    assert build_message(report) == ""
