from __future__ import annotations

import time
from collections.abc import Callable

import httpx

from avherald_scraper.config import DEFAULT_TIMEOUT_SECONDS, USER_AGENT
from avherald_scraper.parser import is_blocked

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class BlockedError(RuntimeError):
    """Raised when avherald.com serves the IP-block / botnet page."""


class Client:
    def __init__(
            self,
            *,
            delay: float = 3.0,
            timeout: float = DEFAULT_TIMEOUT_SECONDS,
            proxy: str | None = None,
            user_agent: str | None = None,
            transport: httpx.BaseTransport | None = None,
            sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.delay = delay
        self._sleeper = sleeper
        self._gets = 0
        headers = dict(DEFAULT_HEADERS)
        if user_agent:
            headers["User-Agent"] = user_agent
        self._http = httpx.Client(
            headers=headers,
            timeout=timeout,
            proxy=proxy,
            transport=transport,
            follow_redirects=True,
            trust_env=True,
        )

    def get(self, url: str) -> str:
        if self._gets > 0 and self.delay > 0:
            self._sleeper(self.delay)
        response = self._http.get(url)
        response.raise_for_status()
        text = response.text
        self._gets += 1
        if is_blocked(text):
            raise BlockedError(
                "avherald.com blocked this IP for unauthorized access. "
                "Set HTTPS_PROXY to an allowed client or wait before retrying."
            )
        return text

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
