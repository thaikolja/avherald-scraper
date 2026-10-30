"""Command-line entry point.

Flags are parsed here, then merged with config.ini. This module does not
fetch pages itself. It calls `scraper.run` and prints what came back.
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

# Annotations can mention types that appear later.
from __future__ import annotations

# The standard library parser. Defaults stay None so config can fill them in.
import argparse

# Database failures raised while a crawl is writing SQLite.
import sqlite3

# Errors go to stderr. The summary stays on stdout.
import sys

# --db and --config are paths.
from pathlib import Path

# Download failures raised by the HTTP client.
import httpx

# Shown by --version. This is the string in __init__.py.
from avherald_scraper import __version__

# Defaults are mentioned in the help text. The loader does the real merge.
from avherald_scraper.config import (
    DEFAULT_DATABASE_PATH,
    DEFAULT_INI_NAME,
    DEFAULT_LIMIT,
    DEFAULT_REQUEST_DELAY_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
    OUTPUT_FORMATS,
    RunConfig,
    load_config,
    parse_categories,
    resolve_ini_path,
)

# A blocked IP is reported on its own, separate from a generic failure.
from avherald_scraper.http import BlockedError

# run() does the crawl. ScrapeResult is what we format afterward.
from avherald_scraper.scraper import ScrapeResult, run

# Help text lists the legal category names from this tuple.
from avherald_scraper.urls import CATEGORIES


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser, including the examples in `--help`."""

    # Raw description so the example block keeps its line breaks.
    parser = argparse.ArgumentParser(
        prog="avherald-scraper",
        description="Save AV Herald listing headlines to SQLite. Does not fetch article bodies.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  avherald-scraper
  avherald-scraper -n 200
  avherald-scraper -c incident -c accident --sort occurrence
  avherald-scraper --dry-run -n 20
  avherald-scraper                 # next run continues where the last one stopped
  avherald-scraper --fresh         # start over from the first list page
  avherald-scraper --config config.ini

Settings live in config.ini. CLI flags win.
""".strip(),
    )

    # Prints the version and exits before any crawl starts.
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    # Optional path. When omitted, load_config looks for config.ini.
    parser.add_argument(
        "--config",
        type=Path,
        help=f"INI settings file (default: ./{DEFAULT_INI_NAME} in the project root)",
    )

    # Group label in `--help`. It doesn't change parsing.
    how_many = parser.add_argument_group("how many")

    # None means "the user didn't pass -n", so config.ini can still set it.
    how_many.add_argument(
        "-n",
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help=f"unique articles to keep (config.ini, else {DEFAULT_LIMIT})",
    )

    # A page cap on top of the article limit. Also defaults to "unset".
    how_many.add_argument(
        "-p",
        "--pages",
        type=int,
        default=None,
        dest="max_pages",
        metavar="N",
        help="stop after N list pages (config.ini, else no page cap)",
    )

    # Second help group: what to fetch.
    what = parser.add_argument_group("what to fetch")

    # append so `-c incident -c accident` and a comma list both work.
    what.add_argument(
        "-c",
        "--category",
        action="append",
        dest="categories",
        metavar="NAME",
        help=f"repeat or comma-separate: {', '.join(CATEGORIES)} (config.ini, else all)",
    )

    # Choices reject a typo before we build a URL.
    what.add_argument(
        "--sort",
        choices=("update", "occurrence"),
        default=None,
        help="list order on avherald.com (config.ini, else update)",
    )

    # Bypasses the sort/category URL builder when you already have a list URL.
    what.add_argument(
        "--start-url",
        default=None,
        help="override the first list URL (skips --sort/--category URL builder)",
    )

    # Third group: where the file goes, and how polite the crawl is.
    where = parser.add_argument_group("where and how")

    # Stored on the namespace as database_path, which is the config field name.
    where.add_argument(
        "-o",
        "--db",
        type=Path,
        default=None,
        dest="database_path",
        help=f"SQLite file (config.ini, else {DEFAULT_DATABASE_PATH})",
    )

    # json, csv, and xlsx are written next to this file. sqlite is the file itself.
    where.add_argument(
        "--format",
        choices=OUTPUT_FORMATS,
        default=None,
        dest="output_format",
        help="output type: sqlite, json, csv, or xlsx (config.ini, else sqlite)",
    )

    # Float, because 0.5 is a legal pause even though the default is 3.
    where.add_argument(
        "-d",
        "--delay",
        type=float,
        default=None,
        help=f"seconds between page requests (config.ini, else {DEFAULT_REQUEST_DELAY_SECONDS})",
    )

    # Repeat the flag, or pass a comma-separated list. CLI replaces the ini list.
    where.add_argument(
        "--proxy",
        action="append",
        default=None,
        metavar="URL",
        help="HTTP(S) proxy URL; repeat or comma-separate (config.ini, else direct)",
    )

    # Passed through to httpx.
    where.add_argument(
        "--timeout",
        type=float,
        default=None,
        help=f"request timeout seconds (config.ini, else {DEFAULT_TIMEOUT_SECONDS})",
    )

    # Replaces the identifiable tool User-Agent.
    where.add_argument(
        "--user-agent",
        default=None,
        dest="user_agent",
        help="override the default User-Agent",
    )

    # BooleanOptionalAction gives both --dry-run and --no-dry-run.
    where.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="parse and print, do not write the database (config.ini, else off)",
    )

    # On by default, but the default is applied later so config.ini can turn it off.
    where.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="continue from the last saved list page (config.ini, else on)",
    )

    # Drops the saved list position when it is also a real write.
    where.add_argument(
        "--fresh",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="ignore the saved position and start from the first list page (config.ini, else off)",
    )

    # Last group: how chatty the process is.
    output = parser.add_argument_group("output")

    # Prints each URL and, together with the summary, the kept rows.
    output.add_argument(
        "-v",
        "--verbose",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="list the kept headlines (config.ini, else off)",
    )

    # Success prints nothing. Errors still go to stderr.
    output.add_argument(
        "-q",
        "--quiet",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="print nothing on success",
    )

    # Prints the merged settings and exits before any download.
    output.add_argument(
        "--show-config",
        action="store_true",
        help="print effective settings and exit",
    )

    # main() parses argv with this.
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one crawl from CLI arguments and return a process status code."""

    # None lets argparse read the real command line. Tests pass a list.
    args = build_parser().parse_args(argv)

    # A bad category or a missing config file is a usage error, not a crash.
    try:
        # Drop the Nones so they don't wipe config.ini values.
        cli = _cli_overrides(args)

        # CLI wins, then config.ini, then built-in defaults.
        config = load_config(cli=cli, config_path=args.config)

    # ValueError is a bad category or sort. FileNotFoundError is --config.
    except (ValueError, FileNotFoundError) as exc:
        # stderr, so a redirected summary doesn't hide the reason.
        print(exc, file=sys.stderr)

        # 2 means the run never started.
        return 2

    # Show the merged settings and stop. No download, no database.
    if args.show_config:
        # Same lookup load_config just used.
        ini_path = resolve_ini_path(config_path=args.config)

        # stdout, so a user can pipe the settings.
        print(_format_show_config(config, ini_path))

        # 0 because this is a successful read, not a crawl.
        return 0

    # From here on, failures are crawl failures.
    try:
        # This downloads list pages and maybe writes SQLite.
        result = run(config)

    # The site served the ban page. The message already says what to try.
    except BlockedError as exc:
        # Same channel as other errors.
        print(exc, file=sys.stderr)

        # 1 means we started, then stopped.
        return 1

    # A failed download, a bad database, or a filesystem error.
    except (httpx.HTTPError, sqlite3.Error, OSError) as exc:
        # Prefix it so a stack-free message is still obviously a failure.
        print(f"scrape failed: {exc}", file=sys.stderr)

        # Also 1. The cause is in the message.
        return 1

    # --quiet skips the summary and the row list.
    if not config.quiet:
        # One paragraph: counts, path, and whether we resumed.
        print(_format_summary(result, config))

        # Dry runs and verbose runs also list the kept rows.
        if config.dry_run or config.verbose:
            # One line per article.
            print(_format_records(result))

    # 0 is success, including "kept nothing".
    return 0


def _cli_overrides(args: argparse.Namespace) -> dict:
    """Copy the flags the user actually set into a dict for load_config."""

    # None means -c was omitted, so a config.ini category list can apply.
    categories = None

    # argparse gives a list of strings when -c was repeated.
    if args.categories:
        # Splits commas, lowercases, and rejects unknown names.
        categories = parse_categories(args.categories)

    # Keys match RunConfig fields. Nones are ignored by the loader.
    return {
        "limit": args.limit,
        "max_pages": args.max_pages,
        "categories": categories,
        "sort": args.sort,
        "start_url": args.start_url,
        "database_path": args.database_path,
        "output_format": args.output_format,
        "delay": args.delay,
        "proxy": args.proxy,
        "timeout": args.timeout,
        "user_agent": args.user_agent,
        "dry_run": args.dry_run,
        "verbose": args.verbose,
        "quiet": args.quiet,
        "resume": args.resume,
        "fresh": args.fresh,
    }


def _format_show_config(config: RunConfig, ini_path: Path | None) -> str:
    """Render the settings a run would use, without starting that run."""

    # Name the file, or say we fell back to built-in defaults.
    source = str(ini_path) if ini_path else "none (built-in defaults)"

    # Empty categories mean the crawl keeps every icon type.
    categories = ", ".join(config.categories) if config.categories else "all"

    # None means there is no page cap.
    pages = str(config.max_pages) if config.max_pages is not None else "none"

    # Count only. The URL can carry credentials.
    proxy = str(len(config.proxies)) if config.proxies else "direct"

    # One fact per line, stable order.
    lines = [
        f"config: {source}",
        f"limit: {config.limit}",
        f"pages: {pages}",
        f"categories: {categories}",
        f"sort: {config.sort}",
        f"database: {config.database_path}",
        f"format: {config.output_format}",
        f"delay: {config.delay}",
        f"timeout: {config.timeout}",
        f"proxy: {proxy}",
        f"resume: {str(config.resume).lower()}",
        f"fresh: {str(config.fresh).lower()}",
        f"dry_run: {str(config.dry_run).lower()}",
        f"start_url: {config.resolved_start_url()}",
    ]

    # The CLI prints this with one print() call.
    return "\n".join(lines)


def _format_summary(result: ScrapeResult, config) -> str:
    """Build the short tally printed after a successful run."""

    # Kept is the number the user asked for. Always show it.
    parts = [f"{len(result.records)} kept"]

    # New rows are the point of the run.
    if result.inserted:
        # Skip the word when nothing was inserted.
        parts.append(f"{result.inserted} new")

    # Updates are rarer. Hide the zero.
    if result.updated:
        # A refresh of a headline already stored.
        parts.append(f"{result.updated} updated")

    # Duplicates did not count toward the limit.
    if result.skipped_duplicate:
        # Only mention them when the crawl actually stepped over some.
        parts.append(f"{result.skipped_duplicate} skipped")

    # Category filter drops. Hidden when the filter matched everything.
    if result.filtered:
        # So a tight category filter does not look like a short site.
        parts.append(f"{result.filtered} filtered")

    # One row of counts.
    lines = ["   ".join(parts)]

    # Dry runs must not look like they wrote the file.
    if config.dry_run:
        # No path, no stored total.
        lines.append("dry-run")

    # A real write names the file the user asked for.
    elif result.export_path is not None:
        # json, csv, or xlsx beside the SQLite store.
        lines.append(str(result.export_path))

    # sqlite is both the store and the output.
    else:
        # stored includes older runs.
        lines.append(f"{config.database_path}   {result.stored} stored")

    # Only when this run opened a saved list page.
    if result.resumed_from:
        # The URL itself is noise. The fact of a resume is enough.
        lines.append("resumed")

    # The CLI prints this as one block.
    return "\n".join(lines)


def _format_records(result: ScrapeResult) -> str:
    """Render the kept rows as aligned text lines."""

    # An empty crawl still needs something to print under the summary.
    if not result.records:
        # Parentheses so it doesn't look like a headline.
        return "(no rows)"

    # Built up and joined, so the caller prints one block.
    lines = []

    # Listing order, which is the order the crawl collected them.
    for record in result.records:
        # A missing date still gets a column.
        date = record.list_date_iso or "?"

        # Same idea for a missing category.
        category = record.category or "?"

        # Fixed width on the category so the headlines line up.
        lines.append(f"{record.article_id}  {date}  {category:<8}  {record.heading}")

    # The CLI prints this with one print() call.
    return "\n".join(lines)
