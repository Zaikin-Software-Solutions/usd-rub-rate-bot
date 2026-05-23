"""Shared base exceptions and a minimal HTTP helper for adapters."""

from __future__ import annotations

from typing import Any

import aiohttp


class RateSourceError(RuntimeError):
    """Raised when a rate source returns an unusable or unreachable response."""


async def fetch_json(
    session: aiohttp.ClientSession,
    url: str,
    *,
    timeout_seconds: float,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
) -> Any:
    """Fetch a URL and parse it as JSON.

    Raises ``RateSourceError`` on any non-2xx response, transport error, or invalid JSON.
    """

    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    try:
        async with session.request(
            method,
            url,
            headers=headers,
            json=json_body,
            timeout=timeout,
        ) as response:
            if response.status >= 400:
                body = await response.text()
                raise RateSourceError(f"HTTP {response.status} from {url}: {body[:200]}")
            try:
                return await response.json(content_type=None)
            except (aiohttp.ContentTypeError, ValueError) as exc:
                raise RateSourceError(f"Invalid JSON from {url}: {exc}") from exc
    except aiohttp.ClientError as exc:
        raise RateSourceError(f"Transport error for {url}: {exc}") from exc
    except TimeoutError as exc:
        raise RateSourceError(f"Timeout fetching {url}") from exc


async def fetch_text(
    session: aiohttp.ClientSession,
    url: str,
    *,
    timeout_seconds: float,
    headers: dict[str, str] | None = None,
) -> str:
    """Fetch a URL and return its body as text. Raises ``RateSourceError`` on failure."""

    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    try:
        async with session.get(url, headers=headers, timeout=timeout) as response:
            if response.status >= 400:
                body = await response.text()
                raise RateSourceError(f"HTTP {response.status} from {url}: {body[:200]}")
            return await response.text()
    except aiohttp.ClientError as exc:
        raise RateSourceError(f"Transport error for {url}: {exc}") from exc
    except TimeoutError as exc:
        raise RateSourceError(f"Timeout fetching {url}") from exc
