# usd-rub-rate-bot

[![CI](https://github.com/Zaikin-Software-Solutions/usd-rub-rate-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/Zaikin-Software-Solutions/usd-rub-rate-bot/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Zaikin-Software-Solutions/usd-rub-rate-bot?display_name=tag&sort=semver&cacheSeconds=300)](https://github.com/Zaikin-Software-Solutions/usd-rub-rate-bot/releases)
[![Docker image](https://img.shields.io/badge/ghcr.io-usd--rub--rate--bot-blue?logo=docker&logoColor=white)](https://github.com/Zaikin-Software-Solutions/usd-rub-rate-bot/pkgs/container/usd-rub-rate-bot)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)

A Telegram bot that periodically publishes USD/RUB cash buy/sell rates from
several Russian sources, alongside the official Central Bank of Russia rate.

## Sources

| Source     | What's published         | Endpoint                                                                      |
| ---------- | ------------------------ | ----------------------------------------------------------------------------- |
| **AkBars** | cash buy / sell USD      | `https://www.akbars.ru/api/v2/offices/bestrates?currencycode=USD&cityFiasRef=…` |
| **T-Bank** | ATM buy / sell USD       | `https://api.tinkoff.ru/v1/currency_rates?from=USD&to=RUB` (category configurable) |
| **CBR**    | official daily USD rate  | with fallback between two mirrors (see below)                                 |

For the CBR rate the bot tries sources **in order**, returning the first that
responds successfully:

1. `https://www.cbr-xml-daily.ru/daily_json.js` — community JSON mirror.
2. `https://www.cbr.ru/scripts/XML_daily.asp` — official XML feed.

If a source is unreachable, its value is rendered as `n/a` in the message
(never `0.00`). Diffs against the CBR rate are computed only for sources that
returned a real value.

## Sample message

```
AkBars (кэш): покупка 73.00 ↓ / продажа 73.60 ↑
T-Bank (кэш): покупка 71.05 ↓ / продажа 75.70 ↑
ЦБ РФ:  71.21
Дифф к ЦБ (покупка): AkBars +1.79 / T-Bank −0.16
Дифф к ЦБ (продажа): AkBars +2.39 / T-Bank +4.49
```

## Prerequisites (all install methods)

- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- The numeric id of a Telegram channel where the bot is admin (e.g. `-1001234567890`)
- A host that can reach Russian sites (AkBars in particular geo-blocks non-RU IPs).
  When running outside RU, point `HTTP_PROXY_URL` at a proxy located in RU.

## Install

### A. Prebuilt image from GHCR (recommended for servers)

CI publishes a multi-arch (`linux/amd64` + `linux/arm64`) image to
`ghcr.io/zaikin-software-solutions/usd-rub-rate-bot` on every push to `main`
and on every `vX.Y.Z` git tag — nothing to build on your side.

Requires only Docker + Docker Compose.

```bash
mkdir -p /opt/usd-rub-rate-bot && cd /opt/usd-rub-rate-bot

# Pull the published compose file and the example env template.
curl -sSL https://raw.githubusercontent.com/Zaikin-Software-Solutions/usd-rub-rate-bot/main/docker-compose.yml -o docker-compose.yml
curl -sSL https://raw.githubusercontent.com/Zaikin-Software-Solutions/usd-rub-rate-bot/main/.env.example -o .env

# Edit .env: TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID are required.
$EDITOR .env

docker compose pull
docker compose up -d
docker compose logs -f
```

Pin to a specific version by replacing `:latest` in `docker-compose.yml` with
`:1.0.0` (or `:1` / `:1.0` for floating major / minor). To update later:
`docker compose pull && docker compose up -d`.

### B. Build with Docker from sources (for local development)

Requires Docker + Docker Compose + `git`.

```bash
git clone https://github.com/Zaikin-Software-Solutions/usd-rub-rate-bot.git
cd usd-rub-rate-bot
cp .env.example .env  # then fill it in
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
docker compose logs -f
```

### C. Run directly with Python (no Docker)

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/)
(`curl -LsSf https://astral.sh/uv/install.sh | sh`).

```bash
git clone https://github.com/Zaikin-Software-Solutions/usd-rub-rate-bot.git
cd usd-rub-rate-bot
cp .env.example .env  # then fill it in
uv sync --extra dev
uv run python -m usd_rub_rate_bot
```

Or via Make: `make install && make run`.

## Configuration

All settings come from environment variables; a `.env` file is read in dev.

| Variable                | Required | Default                                     | Description                                                                 |
| ----------------------- | -------- | ------------------------------------------- | --------------------------------------------------------------------------- |
| `TELEGRAM_BOT_TOKEN`    | yes      | —                                           | Bot token from @BotFather.                                                  |
| `TELEGRAM_CHANNEL_ID`   | yes      | —                                           | Channel id (e.g. `-1001234567890`) or `@channel`.                           |
| `PUBLISH_CRON`          | no       | `* * * * *`                                 | Cron expression (UTC) for the publish schedule.                             |
| `HTTP_TIMEOUT_SECONDS`  | no       | `10`                                        | Outgoing HTTP timeout per source.                                           |
| `TBANK_RATE_CATEGORY`   | no       | `ATMCashoutRateGroup`                       | Which category to pick from T-Bank's response. Default = the ATM cash-exchange rate. |
| `AKBARS_CITY_FIAS_REF`  | no       | `6b1bab7d-ee45-4168-a2a6-4ce2880d90d3` (Kazan) | FIAS reference id of the city for AkBars rates.                          |
| `HTTP_PROXY_URL`        | no       | —                                           | HTTP proxy applied to ALL rate-source requests (not to Telegram). Use when running from an IP range that sources geo-block. Format: `http://user:pass@host:port`. |
| `LOG_LEVEL`             | no       | `INFO`                                      | `DEBUG` / `INFO` / `WARNING` / `ERROR`.                                     |
| `LOG_FORMAT`            | no       | `json`                                      | `json` (prod) or `console` (dev).                                           |

## Project layout

```
src/usd_rub_rate_bot/
  __main__.py             # composition root, scheduler loop
  config.py               # pydantic-settings
  logger.py               # structlog config
  scheduler.py            # APScheduler wiring
  domain/models.py        # CommercialRate, CentralBankRate
  adapters/
    base.py               # RateSourceError + small HTTP helpers
    akbars.py             # AkBars bank
    tbank.py              # T-Bank
    cbr.py                # two CBR sources (JSON + XML)
  services/
    cbr_provider.py       # CBR with cross-source fallback
    aggregator.py         # concurrent fetch from all sources → RatesReport
    message_builder.py    # RatesReport → Telegram text (handles n/a)
    publisher.py          # aggregator + bot.send_message orchestration
tests/                    # pytest, HTTP mocked via aioresponses
```

Architectural choices worth highlighting:

- **Sources fail independently.** Each adapter raises `RateSourceError`; the
  aggregator runs them concurrently and turns failures into `None`. One
  broken source never zeroes out the others — the old bot's `0.0 ₽` bug
  cannot happen here.
- **CBR is hardened with explicit fallback.** A community mirror tends to be
  fast but is occasionally down; the official XML is slower but authoritative.
- **`message_builder` is the only place that knows the wire format.** Anything
  that wants a different layout (HTML, MarkdownV2, etc.) plugs in here.

## Development

```bash
make install     # uv sync --extra dev
make check       # ruff + mypy + pytest
make test
make lint
make format
make typecheck
```

CI runs the same checks on every push and PR, plus a Docker build.

## License

MIT — see [LICENSE](./LICENSE).
