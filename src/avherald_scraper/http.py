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
            proxies: tuple[str, ...] | list[str] = (),
            user_agent: str | None = None,
            transport: httpx.BaseTransport | None = None,
            sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        """Remember the pause, the proxy list, and how to actually sleep."""

        # Seconds to wait before the second page, not between proxy retries.
        self.delay = delay

        # Tests pass a fake sleeper so they don't really wait.
        self._sleeper = sleeper

        # Counts finished downloads so the first page can skip the pause.
        self._gets = 0

        # One leftover string argument still means a single proxy.
        if proxy and not proxies:
            # The scraper passes the tuple. Tests sometimes pass one string.
            proxies = (proxy,)

        # Try these in order. Empty means a direct connection.
        self._proxies = tuple(proxies)

        # Index of the proxy the open client is using.
        self._index = 0

        # Reused when we open the next proxy after a ban.
        self._timeout = timeout

        # Reused for the same reason. Tests pass a mock transport.
        self._transport = transport

        # Copy the defaults so a custom User-Agent doesn't leak into them.
        self._headers = dict(DEFAULT_HEADERS)

        # Only replace the header when the caller actually passed one.
        if user_agent:
            # This is the string the site will see.
            self._headers["User-Agent"] = user_agent

        # Open the first proxy, or a direct client when the list is empty.
        self._open()

    def _current_proxy(self) -> str | None:
        """Return the proxy in use, or None for a direct connection."""

        # No list means we never send traffic through a proxy.
        if not self._proxies:
            # httpx treats None as a direct connection.
            return None

        # The index only moves forward.
        return self._proxies[self._index]

    def _open(self) -> None:
        """Open an HTTP client for the current proxy."""

        # follow_redirects covers the odd hop. Settings supply the proxy.
        self._http = httpx.Client(
            headers=self._headers,
            timeout=self._timeout,
            proxy=self._current_proxy(),
            transport=self._transport,
            follow_redirects=True,
            trust_env=False,
        )

    def _rotate(self) -> bool:
        """Switch to the next proxy. False when this was the last one."""

        # Nothing left to try.
        if self._index + 1 >= len(self._proxies):
            # The caller raises the error from this host.
            return False

        # The next host in the configured order.
        self._index += 1

        # Drop connections that the banned host still holds.
        self._http.close()

        # The following request uses the new proxy.
        self._open()

        # The same URL can be tried again.
        return True

    def get(self, url: str) -> str | None:
        """Download `url` and return the HTML.

        A ban page or a transport error tries the next proxy. When every
        proxy has failed, the last error is raised.
        """

        # One pause per page, not per proxy retry.
        slept = False

        # At least one attempt. Extra attempts exist only when more proxies do.
        while True:
            # Give the site a breather after the previous successful page.
            if self._gets > 0 and self.delay > 0 and not slept:
                # `delay` of 0 is the "don't pause" switch, used by some tests.
                self._sleeper(self.delay)

                # Retries of this same URL must not sleep again.
                slept = True

            # One GET. Redirects are already allowed on the client.
            try:
                # The open client targets the current proxy.
                response = self._http.get(url)

                # A 4xx or 5xx should try the next proxy instead of being parsed.
                response.raise_for_status()

                # The parser wants text, not bytes.
                text = response.text

            # Network, timeout, and HTTP status failures can move to the next host.
            except httpx.HTTPError:
                # Last proxy: surface the error.
                if not self._rotate():
                    # Nothing else to try.
                    raise

                # Same URL, next proxy.
                continue

            # Count this download so the next page knows it should wait.
            self._gets += 1

            # The block page is HTML with a 200 status, so the status check misses it.
            if is_blocked(text):
                # A ban uses up this proxy.
                if not self._rotate():
                    # Every configured host is blocked, or there was no proxy.
                    raise BlockedError(
                        "avherald.com blocked this IP for unauthorized access. "
                        "Add another proxy in config.ini or pass --proxy, "
                        "or wait before retrying."
                    )

                # The ban page is not a successful download.
                self._gets -= 1

                # Same URL, next proxy.
                continue

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
