"""Merge CLI flags with config.ini.

Highest priority wins: flags, then `config.ini`, then the built-in RunConfig
defaults. Environment variables and `.env` files are not read.
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

# Annotations in this file can mention types defined further down.
from __future__ import annotations

# config.ini in the project root. The section titles are for people.
import configparser

# Used to type the mappings this loader accepts.
from collections.abc import Mapping

# RunConfig is frozen. replace() is how a layer of settings is applied.
from dataclasses import dataclass, replace

# Database and config paths are pathlib objects by the time we finish.
from pathlib import Path

# The loader accepts any mapping, not just argparse.
from typing import Any

# Category names and the list-URL builder live with the other URL rules.
from avherald_scraper.urls import CATEGORIES, SITE_ORIGIN, list_page_url

# Public site. config.ini can replace this.
DEFAULT_BASE_URL = SITE_ORIGIN

# Relative to the working directory, not to this source file.
DEFAULT_DATABASE_PATH = Path("data/avherald.sqlite")

# Seconds between list pages. The first request does not wait.
DEFAULT_REQUEST_DELAY_SECONDS = 3.0

# How many new headlines one run keeps when nobody says otherwise.
DEFAULT_LIMIT = 50

# Passed to httpx. A hung connection should not stall forever.
DEFAULT_TIMEOUT_SECONDS = 20.0

# Shipped at the repository root. CLI flags override whatever it sets.
DEFAULT_INI_NAME = "config.ini"

# Identifies the tool. It does not pretend to be a browser.
USER_AGENT = (
    "avherald-scraper/2.0 (+https://github.com/thaikolja/avherald-scraper; "
    "headlines-only personal archive)"
)


# Frozen so a run can't quietly mutate the settings it started with.
@dataclass(frozen=True)
class RunConfig:
    """Every knob for one crawl, after the sources have been merged."""

    # Kept so the class body defines the name. The dataclass decorator replaces it.
    __dataclass_fields__ = None

    # Unique articles to keep. Duplicates do not count toward this.
    limit: int = DEFAULT_LIMIT

    # Pause between downloads, in seconds.
    delay: float = DEFAULT_REQUEST_DELAY_SECONDS

    # Where the SQLite file goes.
    database_path: Path = DEFAULT_DATABASE_PATH

    # Site origin. The path and query are added later.
    base_url: str = DEFAULT_BASE_URL

    # When set, sort and category are not used to build the first URL.
    start_url: str | None = None

    # `update` or `occurrence`.
    sort: str = "update"

    # Empty means every category.
    categories: tuple[str, ...] = ()

    # None means "no page cap", only the article limit.
    max_pages: int | None = None

    # HTTP(S) proxies, in try order. Empty means a direct connection.
    proxies: tuple[str, ...] = ()

    # Per-request timeout in seconds.
    timeout: float = DEFAULT_TIMEOUT_SECONDS

    # Sent on every listing request.
    user_agent: str = USER_AGENT

    # Parse and print, but do not insert, update, or move the bookmark.
    dry_run: bool = False

    # Print each fetched URL.
    verbose: bool = False

    # Skip the success summary.
    quiet: bool = False

    # Continue from the saved list page.
    resume: bool = True

    # Ignore that saved page and start at the first list page.
    fresh: bool = False

    def resolved_start_url(self) -> str:
        """Return the first list URL, either the override or a built one."""

        # --start-url, or start_url in config.ini, skips the bitfield builder.
        if self.start_url:
            # Used as-is. The caller is responsible for it being a list page.
            return self.start_url

        # Homepage when sort is update and no category is selected.
        return list_page_url(self.base_url, sort=self.sort, categories=self.categories)

    def crawl_key(self) -> str:
        """Return the bookmark key for this sort, category set, and start URL."""

        # `*` means "all categories", so that bookmark doesn't collide with a filter.
        cats = ",".join(self.categories) or "*"

        # A custom start URL is part of the key. Same filters, different URL, different bookmark.
        if self.start_url:
            # The categories still matter, because they filter rows after download.
            return f"url|{self.start_url}|{cats}"

        # The usual key. `update|*` is the default crawl.
        return f"{self.sort}|{cats}"


def parse_categories(value: str | list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    """Normalize category names into a unique lowercase tuple.

    A string may contain commas. A list may contain commas inside its items.
    Unknown names raise ValueError. None and blanks become an empty tuple,
    which means "every category".
    """

    # None and "" both mean the filter is off.
    if not value:
        # Empty tuple is what RunConfig stores for "all".
        return ()

    # A single string is treated like a one-item list from here on.
    raw = [value] if isinstance(value, str) else list(value)

    # Pieces after splitting commas.
    parts: list[str] = []

    # `-c incident,accident` and `-c incident -c accident` both land here.
    for item in raw:
        # Split, trim, and lowercase each piece.
        parts.extend(piece.strip().lower() for piece in item.split(","))

    # Blank pieces from a trailing comma are ignored below. Real typos are not.
    unknown = [part for part in parts if part and part not in CATEGORIES]

    # Fail before any page is fetched.
    if unknown:
        # List the bad names and the legal ones together.
        raise ValueError(
            "unknown category: "
            + ", ".join(unknown)
            + f" (choose from {', '.join(CATEGORIES)})"
        )

    # First-seen order, so the crawl key is stable for the same set.
    seen: set[str] = set()

    # The result, without duplicates.
    ordered: list[str] = []

    # Walk the pieces once.
    for part in parts:
        # Drop blanks and names we already kept.
        if not part or part in seen:
            # The next piece might still be new.
            continue

        # Remember it so a repeat doesn't get a second slot.
        seen.add(part)

        # Preserve the order the user wrote.
        ordered.append(part)

    # Tuples suit a frozen config.
    return tuple(ordered)


def parse_proxies(value: str | list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    """Normalize one proxy string, or several, into a unique tuple.

    A string may contain commas. A list may contain commas inside its items.
    Blank pieces are dropped. Order is the order they should be tried.
    """

    # None and "" both mean a direct connection.
    if not value:
        # Empty tuple is what RunConfig stores for "no proxy".
        return ()

    # A single string is treated like a one-item list from here on.
    raw = [value] if isinstance(value, str) else list(value)

    # Pieces after splitting commas.
    parts: list[str] = []

    # `--proxy a --proxy b,c` both land here.
    for item in raw:
        # Split and trim each piece.
        parts.extend(piece.strip() for piece in str(item).split(","))

    # First-seen order, so failover is stable.
    seen: set[str] = set()

    # The result, without duplicates.
    ordered: list[str] = []

    # Walk the pieces once.
    for part in parts:
        # Drop blanks and hosts we already kept.
        if not part or part in seen:
            # The next piece might still be new.
            continue

        # Remember it so a repeat doesn't get a second slot.
        seen.add(part)

        # Preserve the order the user wrote.
        ordered.append(part)

    # Tuples suit a frozen config.
    return tuple(ordered)


def resolve_ini_path(
        cwd: Path | None = None,
        config_path: str | Path | None = None,
) -> Path | None:
    """Return the config.ini this run would read, if that file exists."""

    # Same rules as load_config, so --show-config names the real file.
    root = cwd or Path.cwd()

    # None means built-in defaults only.
    return _resolve_ini_path(root, config_path)


def load_config(
        *,
        cli: Mapping[str, Any] | None = None,
        config_path: str | Path | None = None,
        cwd: Path | None = None,
) -> RunConfig:
    """Build a RunConfig from config.ini, then CLI flags.

    Each layer only overwrites values it actually sets. None is ignored, so
    an omitted flag does not erase a value from config.ini.
    """

    # Tests pass a temporary directory. The command line uses the real cwd.
    root = cwd or Path.cwd()

    # --config picks a file. Otherwise use config.ini at the project root.
    ini_path = _resolve_ini_path(root, config_path)

    # Start from the dataclass defaults.
    config = RunConfig()

    # A checkout without that file just keeps the built-in defaults.
    if ini_path is not None:
        # Blank and commented keys are left unset.
        config = _apply(config, _read_ini(ini_path))

    # Flags beat the ini file.
    if cli:
        # A copy, so we don't surprise the caller by popping their mapping.
        config = _apply(config, dict(cli))

    # Frozen result for the crawl.
    return config


def _resolve_ini_path(cwd: Path, config_path: str | Path | None = None) -> Path | None:
    """Find config.ini, or the file passed to --config.

    An explicit path that isn't a file is an error. A missing default file
    is fine and just means "use built-in defaults".
    """

    # --config was passed.
    if config_path is not None:
        # Don't require the file to sit in cwd. The path can be anywhere.
        path = Path(config_path)

        # A typo should fail, not silently use defaults.
        if not path.is_file():
            # main() turns this into exit code 2.
            raise FileNotFoundError(f"config file not found: {path}")

        # This replaces the project config.ini for this run.
        return path

    # Running from the project root hits the file directly.
    direct = cwd / DEFAULT_INI_NAME

    # That is the usual case, including the tests that write a temporary file.
    if direct.is_file():
        # No need to walk parents.
        return direct

    # A subdirectory run should still see the copy at the project root.
    for parent in cwd.parents:
        # pyproject.toml marks the project. A random config.ini further up does not.
        if (parent / "pyproject.toml").is_file() and (parent / DEFAULT_INI_NAME).is_file():
            # This is the shipped file.
            return parent / DEFAULT_INI_NAME

    # No project file in sight.
    return None


def _normalize_file_keys(data: dict[str, Any]) -> dict[str, Any]:
    """Rename file aliases onto RunConfig field names."""

    # The ini file says `database`. The field is database_path.
    if "database" in data and "database_path" not in data:
        # Pop so the alias is not dropped later as an unknown key.
        data["database_path"] = data.pop("database")

    # Ready for _apply.
    return data


def _read_ini(path: Path) -> dict[str, Any]:
    """Read config.ini into a dict the config applier understands."""

    # No interpolation, so a percent sign in a proxy URL stays put.
    parser = configparser.ConfigParser(interpolation=None)

    # UTF-8, same encoding as the file in the repository.
    parser.read(path, encoding="utf-8")

    # Section names are documentation. The keys are what we apply.
    found: dict[str, Any] = {}

    # Every section is flattened into one mapping.
    for section in parser.sections():
        # Values arrive as strings. Empty means the setting was left blank.
        for key, value in parser.items(section):
            # A blank value does not override a lower layer.
            if not value.strip():
                # Optional settings are written this way.
                continue

            # _apply turns the text into ints, floats, bools, and paths.
            found[key] = value.strip()

    # `database` becomes database_path.
    return _normalize_file_keys(found)


def _as_bool(value: str) -> bool:
    """True for 1, true, yes, and on. Everything else is false."""

    # Case and surrounding space don't matter.
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _apply(config: RunConfig, updates: Mapping[str, Any]) -> RunConfig:
    """Return a new RunConfig with recognised updates copied onto `config`.

    Unknown keys and Nones are ignored. That is what lets an omitted CLI flag
    fall through to config.ini.
    """

    # Only real fields. A typo in the ini file should not crash with TypeError.
    allowed = set(RunConfig.__dataclass_fields__)

    # The dict replace() will actually receive.
    cleaned: dict[str, Any] = {}

    # Walk whatever this layer provided.
    for key, value in updates.items():
        # The ini file and the flag both say `proxy`. The field is `proxies`.
        if key == "proxy":
            # One name from here on.
            key = "proxies"

        # None means "this layer didn't set it".
        if key not in allowed or value is None:
            # Skip, and leave the lower layer's value in place.
            continue

        # Keep it for the conversion step below.
        cleaned[key] = value

    # Proxies arrive as a string, a list, or a tuple depending on the source.
    if "proxies" in cleaned:
        # Commas are split and blanks are dropped.
        cleaned["proxies"] = parse_proxies(cleaned["proxies"])

    # Categories arrive as a string, a list, or a tuple depending on the source.
    if "categories" in cleaned:
        # Duplicates are removed and unknown names raise.
        cleaned["categories"] = parse_categories(cleaned["categories"])

    # The field is a Path even when the user typed a string.
    if "database_path" in cleaned:
        # Relative paths stay relative to the working directory.
        cleaned["database_path"] = Path(cleaned["database_path"])

    # Stored without a trailing slash so URL joins don't double up.
    if "base_url" in cleaned:
        # str() covers a pathlib value a caller might pass in.
        cleaned["base_url"] = str(cleaned["base_url"]).rstrip("/")

    # Only two spellings are legal, and case doesn't matter.
    if "sort" in cleaned:
        # Compared against the lowercase names.
        sort = str(cleaned["sort"]).lower()

        # A bad sort is a configuration error.
        if sort not in ("update", "occurrence"):
            # main() prints this and exits 2.
            raise ValueError("sort must be 'update' or 'occurrence'")

        # Store the normalized spelling.
        cleaned["sort"] = sort

    # Zero or negative means "no page cap".
    if "max_pages" in cleaned:
        # The ini file gives a string. int() covers that and a real int.
        pages = int(cleaned["max_pages"])

        # None is what the crawl loop treats as unlimited.
        cleaned["max_pages"] = pages if pages > 0 else None

    # The article cap is always an int after this.
    if "limit" in cleaned:
        # A bad value raises and aborts the run.
        cleaned["limit"] = int(cleaned["limit"])

    # The pause is a float so fractions of a second work.
    if "delay" in cleaned:
        # "3" and 3.0 both become 3.0.
        cleaned["delay"] = float(cleaned["delay"])

    # Same for the httpx timeout.
    if "timeout" in cleaned:
        # Units are seconds.
        cleaned["timeout"] = float(cleaned["timeout"])

    # Flags may already be bools from argparse, or strings from config.ini.
    for flag in ("dry_run", "verbose", "quiet", "resume", "fresh"):
        # Only convert the ones this layer actually set.
        if flag in cleaned and not isinstance(cleaned[flag], bool):
            # "yes" becomes True. "no" becomes False.
            cleaned[flag] = _as_bool(str(cleaned[flag]))

    # New object. The one we were given stays as it was.
    return replace(config, **cleaned)
