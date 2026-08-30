from __future__ import annotations

import argparse
import sys
from pathlib import Path

from avherald_scraper import __version__
from avherald_scraper.config import (
    DEFAULT_CONFIG_NAME,
    DEFAULT_DATABASE_PATH,
    DEFAULT_LIMIT,
    DEFAULT_REQUEST_DELAY_SECONDS,
    load_config,
    parse_categories,
)
from avherald_scraper.http import BlockedError
from avherald_scraper.scraper import ScrapeResult, run
from avherald_scraper.urls import CATEGORIES


def build_parser() -> argparse.ArgumentParser:
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
  avherald-scraper --config avherald.toml

Put defaults in avherald.toml (cwd) or .env. CLI flags win.
""".strip(),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--config",
        type=Path,
        help=f"TOML config file (default: ./{DEFAULT_CONFIG_NAME} if present)",
    )

    how_many = parser.add_argument_group("how many")
    how_many.add_argument(
        "-n",
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help=f"unique articles to keep (default: {DEFAULT_LIMIT})",
    )
    how_many.add_argument(
        "-p",
        "--pages",
        type=int,
        default=None,
        dest="max_pages",
        metavar="N",
        help="stop after N list pages (default: no page cap)",
    )

    what = parser.add_argument_group("what to fetch")
    what.add_argument(
        "-c",
        "--category",
        action="append",
        dest="categories",
        metavar="NAME",
        help=f"repeat or comma-separate: {', '.join(CATEGORIES)}",
    )
    what.add_argument(
        "--sort",
        choices=("update", "occurrence"),
        default=None,
        help="list order on avherald.com (default: update)",
    )
    what.add_argument(
        "--start-url",
        default=None,
        help="override the first list URL (skips --sort/--category URL builder)",
    )

    where = parser.add_argument_group("where and how")
    where.add_argument(
        "-o",
        "--db",
        type=Path,
        default=None,
        dest="database_path",
        help=f"SQLite file (default: {DEFAULT_DATABASE_PATH})",
    )
    where.add_argument(
        "-d",
        "--delay",
        type=float,
        default=None,
        help=f"seconds between page requests (default: {DEFAULT_REQUEST_DELAY_SECONDS})",
    )
    where.add_argument("--proxy", default=None, help="HTTP(S) proxy URL")
    where.add_argument("--timeout", type=float, default=None, help="request timeout seconds")
    where.add_argument(
        "--user-agent",
        default=None,
        dest="user_agent",
        help="override the default User-Agent",
    )
    where.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="parse and print, do not write the database",
    )
    where.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="continue from the last saved list page (default: on)",
    )
    where.add_argument(
        "--fresh",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="ignore the saved position and start from the first list page",
    )

    output = parser.add_argument_group("output")
    output.add_argument(
        "-v",
        "--verbose",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="print each fetched URL",
    )
    output.add_argument(
        "-q",
        "--quiet",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="print nothing on success",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cli = _cli_overrides(args)
        config = load_config(cli=cli, config_path=args.config)
    except (ValueError, FileNotFoundError) as exc:
        print(exc, file=sys.stderr)
        return 2

    try:
        result = run(config)
    except BlockedError as exc:
        print(exc, file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"scrape failed: {exc}", file=sys.stderr)
        return 1

    if not config.quiet:
        print(_format_summary(result, config))
        if config.dry_run or config.verbose:
            print(_format_records(result))
    return 0


def _cli_overrides(args: argparse.Namespace) -> dict:
    categories = None
    if args.categories:
        categories = parse_categories(args.categories)
    return {
        "limit": args.limit,
        "max_pages": args.max_pages,
        "categories": categories,
        "sort": args.sort,
        "start_url": args.start_url,
        "database_path": args.database_path,
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


def _format_summary(result: ScrapeResult, config) -> str:
    counts = result.category_counts()
    breakdown = ", ".join(f"{name} {n}" for name, n in sorted(counts.items())) or "none"
    target = "dry-run (not saved)" if config.dry_run else str(config.database_path)
    resumed = f" Resumed from {result.resumed_from}." if result.resumed_from else ""
    return (
        f"Kept {len(result.records)} of {result.parsed} listing row(s) "
        f"from {result.pages_fetched} page(s) ({breakdown}). "
        f"inserted {result.inserted}, updated {result.updated}, "
        f"skipped {result.skipped_duplicate} duplicate(s), "
        f"filtered {result.filtered}. "
        f"{target}: {result.stored} stored.{resumed}"
    )


def _format_records(result: ScrapeResult) -> str:
    if not result.records:
        return "(no rows)"
    lines = []
    for record in result.records:
        date = record.list_date_iso or "?"
        category = record.category or "?"
        lines.append(f"{record.article_id}  {date}  {category:<8}  {record.heading}")
    return "\n".join(lines)
