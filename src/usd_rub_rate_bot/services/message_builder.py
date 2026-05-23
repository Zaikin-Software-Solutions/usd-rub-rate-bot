"""Format a Telegram message from a RatesReport."""

from __future__ import annotations

from usd_rub_rate_bot.domain.models import CentralBankRate, CommercialRate
from usd_rub_rate_bot.services.aggregator import RatesReport

NA = "n/a"


def build_message(report: RatesReport) -> str:
    """Render the Telegram message.

    Layout:

        AkBars: покупка 73.00 ↓ / продажа 73.60 ↑
        T-Bank (кэш): покупка 71.05 ↓ / продажа 75.70 ↑
        ЦБ РФ:  71.21
        Дифф к ЦБ (покупка): AkBars +1.79 / T-Bank −0.16
        Дифф к ЦБ (продажа): AkBars +2.39 / T-Bank +4.49

    Missing sources show ``n/a`` and are excluded from diffs.
    Returns an empty string if no source produced data — callers skip publishing.
    """

    if not report.has_any():
        return ""

    lines = [
        _commercial_line("AkBars (кэш)", report.akbars),
        _commercial_line("T-Bank (кэш)", report.tbank),
        _cbr_line(report.cbr),
    ]

    buy_diff = _diff_line(report, kind="buy")
    if buy_diff:
        lines.append(buy_diff)

    sell_diff = _diff_line(report, kind="sell")
    if sell_diff:
        lines.append(sell_diff)

    return "\n".join(lines)


def _commercial_line(label: str, rate: CommercialRate | None) -> str:
    if rate is None:
        return f"{label}: {NA}"
    return f"{label}: покупка {_fmt(rate.buy)} ↓ / продажа {_fmt(rate.sell)} ↑"


def _cbr_line(rate: CentralBankRate | None) -> str:
    if rate is None:
        return f"ЦБ РФ:  {NA}"
    return f"ЦБ РФ:  {_fmt(rate.value)}"


def _diff_line(report: RatesReport, *, kind: str) -> str:
    """Build a diff line for either 'buy' or 'sell' against the CBR rate."""

    if report.cbr is None:
        return ""

    parts: list[str] = []
    for label, rate in (("AkBars", report.akbars), ("T-Bank", report.tbank)):
        if rate is None:
            continue
        commercial_value = rate.buy if kind == "buy" else rate.sell
        diff = commercial_value - report.cbr.value
        parts.append(f"{label} {_fmt_signed(diff)}")

    if not parts:
        return ""

    title = "Дифф к ЦБ (покупка)" if kind == "buy" else "Дифф к ЦБ (продажа)"
    return f"{title}: " + " / ".join(parts)


def _fmt(value: float) -> str:
    return f"{value:.2f}"


def _fmt_signed(value: float) -> str:
    return f"{'+' if value >= 0 else '−'}{abs(value):.2f}"
