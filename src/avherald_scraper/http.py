"""Download one listing page at a time, and pause between them.

The first request goes out immediately. Later ones wait, so a crawl does not
hammer the site. A block page is an error, not HTML to parse.
"""

#  @name:           The Aviation Herald (avherald)
#  @description     Unofficial CLI tool to scrape data from avherald.com and store it in a .sqlite database.
#  @author          Kolja Nolte <kolja.nolte@gmail.com>
#  @copyright       2025-2026 (C) Kolja Nolte
#  @see             https://docs.kolja-nolte.com/av-herald
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  Released under the GNU General Public License v2 or later.
#  See: https://www.gnu.org/licenses/gpl-2.0.html
#
#  @package AVH
#  @license GPL-2.0-or-later

# Annotations can refer to classes defined further down.
from __future__ import annotations

# The default sleeper is the real clock.
import time

# The sleeper argument is typed as "some function that takes a float".
from collections.abc import Callable

# `__enter__` returns this object, including a subclass.
from typing import Self

# HTTP client. Tests swap in a fake transport so nothing hits the network.
import httpx

# Timeout and the User-Agent string live with the rest of the defaults.
from avherald_scraper.config import DEFAULT_TIMEOUT_SECONDS, USER_AGENT

# The block page is detected from its wording, over in the parser.
from avherald_scraper.parser import is_blocked

# Sent with every request unless the caller overrides the User-Agent.
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class BlockedError(RuntimeError):
    """The site answered with its unauthorized-access page."""


class Client:
    """A small httpx wrapper that waits between list-page downloads."""

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
        """Remember the pause, the proxy, and how to actually sleep."""

        # Seconds to wait before the second request and every one after that.
        self.delay = delay

        # Tests pass a fake sleeper so they don't really wait.
        self._sleeper = sleeper

        # Counts finished downloads so the first one can skip the pause.
        self._gets = 0

        # Copy the defaults so a custom User-Agent doesn't leak into them.
        headers = dict(DEFAULT_HEADERS)

        # Only replace the header when the caller actually passed one.
        if user_agent:
            # This is the string the site will see.
            headers["User-Agent"] = user_agent

        # follow_redirects covers the odd hop. The proxy comes only from settings.
        self._http = httpx.Client(
            headers=headers,
            timeout=timeout,
            proxy=proxy,
            transport=transport,
            follow_redirects=True,
            trust_env=False,
        )

    def get(self, url: str) -> str:
        """Download `url` and return the HTML, or raise if the IP is blocked."""

        # Give the site a breather after the first page.
        if self._gets > 0 and self.delay > 0:
            # `delay` of 0 is the "don't pause" switch, used by some tests.
            self._sleeper(self.delay)

        # One GET. Redirects are already allowed on the client.
        response = self._http.get(url)

        # A 4xx or 5xx should stop the crawl instead of being parsed.
        response.raise_for_status()

        # The parser wants text, not bytes.
        text = response.text

        # Count this download so the next call knows it should wait.
        self._gets += 1

        # The block page is HTML with a 200 status, so the status check misses it.
        if is_blocked(text):
            # Tell the CLI to stop and mention the proxy option.
            raise BlockedError(
                "avherald.com blocked this IP for unauthorized access. "
                "Set proxy in config.ini or pass --proxy, or wait before retrying."
            )

        # Normal listing HTML.
        return text

    def close(self) -> None:
        """Close the underlying connection pool."""

        # Safe to call when the crawl is finished or when it failed.
        self._http.close()

    def __enter__(self) -> Self:
        """Let `with Client(...)` hand back this same object."""

        # Nothing to set up. `__init__` already opened the httpx client.
        return self

    def __exit__(self, *exc: object) -> None:
        """Close the client when the `with` block ends, error or not."""

        # The exception, if there was one, is left for the caller.
        self.close()
