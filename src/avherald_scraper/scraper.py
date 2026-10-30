"""Walk listing pages until the limit, the page cap, or the end of the list.

Stored ids are skipped and do not count toward the limit. The bookmark in
`crawl_state` is what makes the next run continue instead of starting over.
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

# Annotations can mention classes defined further down.
from __future__ import annotations

# Progress goes to stderr so the summary on stdout stays pipe-friendly.
import sys

# The bar keeps redrawing while a page request is blocked.
import threading

# Used only to tally categories for the CLI summary.
from collections import Counter

# ScrapeResult is frozen. _Crawl is the mutable scratchpad while we walk.
from dataclasses import dataclass

# The database path may be a string from config.ini.
from pathlib import Path

# HtmlFetcher is a small protocol so tests can pass a fake downloader.
from typing import Protocol

# Every knob for one run, already merged from the CLI and config.ini.
from avherald_scraper.config import RunConfig

# Opened unless this is a dry run against a database that doesn't exist yet.
from avherald_scraper.db import Database

# The real downloader. Tests inject their own and never construct this.
from avherald_scraper.http import Client

# What the parser returns, and what we eventually store.
from avherald_scraper.models import ArticleRecord

# One listing page in, rows and a next URL out.
from avherald_scraper.parser import parse_list_page


# The crawl only needs something that can download a page.
class HtmlFetcher(Protocol):
    """Anything with a `get` method that returns HTML."""

    # Download one page. The real client and the tests both do this.
    def get(self, url: str) -> str:
        """Download one page and return its HTML."""

        # The real client and the test double both satisfy this.
        ...


# Frozen so the CLI can print the result without worrying it will change.
@dataclass(frozen=True)
class ScrapeResult:
    """What one run saw, and what it did to the database."""

    # List pages actually downloaded.
    pages_fetched: int

    # Rows the parser returned, before skip and category filters.
    parsed: int

    # Brand-new article ids written this run.
    inserted: int

    # Ids that were already stored and got a refresh.
    updated: int

    # How many rows the database holds after the run.
    stored: int

    # Ids we already had, so they did not count toward the limit.
    skipped_duplicate: int

    # Rows dropped because their category was not requested.
    filtered: int = 0

    # The rows this run kept, in listing order.
    records: tuple[ArticleRecord, ...] = ()

    # The bookmark URL we started from, when this run resumed.
    resumed_from: str | None = None

    # Tally the kept rows by category for the summary line.
    def category_counts(self) -> dict[str, int]:
        """Count the kept rows by category name."""

        # Missing categories are lumped under "unknown" so the summary still adds up.
        counts: Counter[str] = Counter(
            record.category or "unknown" for record in self.records
        )

        # A plain dict is easier for the CLI to sort.
        return dict(counts)


# Mutable on purpose. The walk fills it in as pages come back.
@dataclass
class _Crawl:
    """Scratch state for one page walk, before it becomes a ScrapeResult."""

    # Rows that passed the filters and were not already stored.
    records: list[ArticleRecord]

    # Pages downloaded during this walk.
    pages_fetched: int

    # Parser rows seen, including ones we later skipped.
    parsed: int

    # Already-stored ids encountered.
    skipped: int

    # Rows rejected by the category filter.
    filtered: int

    # Where the next run should start. None means "no next page".
    resume_url: str | None

    # Last id we actually kept. Stored on the bookmark.
    last_article_id: str | None

    # True when we believe this filter combo has been fully walked.
    completed: bool

    # Set when we opened a saved URL instead of the first list page.
    resumed_from: str | None


# Download listing pages and, unless this is a dry run, write them to SQLite.
def run(config: RunConfig, *, client: HtmlFetcher | None = None) -> ScrapeResult:
    """Crawl listing pages and, unless this is a dry run, write SQLite."""

    # True when we created the HTTP client and therefore must close it.
    owned_client = False

    # A test can pass its own fetcher. The command line never does.
    fetcher = client

    # No fake client means we talk to the network ourselves.
    if fetcher is None:
        # Delay, proxy, and User-Agent all come from the merged config.
        fetcher = Client(
            delay=config.delay,
            timeout=config.timeout,
            proxies=config.proxies,
            user_agent=config.user_agent,
        )

        # Remember to close it in the finally block.
        owned_client = True

    # Stays None when a dry run has no database file to read.
    db: Database | None = None

    # Accept either a Path or a string from config.ini.
    path = Path(config.database_path)

    # A dry run still opens an existing file so it can skip stored ids.
    if not config.dry_run or path.exists():
        # This creates the parent directory.
        db = Database(path)

        # New files get the articles and crawl_state tables.
        db.init()

        # `--fresh` drops the bookmark, but a dry run must not delete it.
        if config.fresh and not config.dry_run:
            # Only this sort/category key. Other bookmarks stay.
            db.clear_checkpoint(config.crawl_key())

    # Draws on a terminal. Quiet runs and pipes leave it blank.
    progress = _Progress(config)

    # The database and the HTTP client both need closing if we opened them.
    try:
        # Walk pages until the limit, the page cap, or the end of the list.
        crawl = _crawl(fetcher, config=config, db=db, progress=progress)

        # Dry runs report zeros for the write counters.
        inserted = updated = stored = 0

        # Writing is skipped entirely on a dry run, and when there is no database.
        if not config.dry_run and db is not None:
            # Inserts and updates share one transaction.
            inserted, updated = db.upsert_many(crawl.records)

            # The next invocation reads this bookmark back.
            db.save_checkpoint(
                config.crawl_key(),
                resume_url=crawl.resume_url,
                last_article_id=crawl.last_article_id,
                completed=crawl.completed,
            )

            # Includes rows from older runs, not just this one.
            stored = db.count()

    # Close even when the download or the parser raises.
    finally:
        # End the bar line so the next message starts on a fresh row.
        progress.close()

        # A dry run with no existing file never opened a connection.
        if db is not None:
            # Release the SQLite file before we return.
            db.close()

        # The test double might not have a close method. That's fine.
        close = getattr(fetcher, "close", None)

        # Only close a client we constructed. The caller owns an injected one.
        if owned_client and callable(close):
            # Shuts the httpx pool.
            close()

    # Freeze the walk into the object the CLI prints.
    result = ScrapeResult(
        pages_fetched=crawl.pages_fetched,
        parsed=crawl.parsed,
        inserted=inserted,
        updated=updated,
        stored=stored,
        skipped_duplicate=crawl.skipped,
        filtered=crawl.filtered,
        records=tuple(crawl.records),
        resumed_from=crawl.resumed_from,
    )

    # The CLI formats this for humans.
    return result


def render_progress(*, kept: int, limit: int, skipped: int, width: int = 20) -> str:
    """Build the progress bar text for one moment in the crawl."""

    # A zero limit would divide by zero. Treat it as a full bar once anything is kept.
    total = limit if limit > 0 else max(kept, 1)

    # Never draw past the end of the track.
    filled = int(width * min(kept, total) / total)

    # Block characters when the terminal can print them. Otherwise ASCII.
    full, empty = _bar_glyphs()

    # The track itself.
    bar = full * filled + empty * (width - filled)

    # Skipped ids matter only when there were some.
    extra = f"  skipped {skipped}" if skipped else ""

    # kept/limit is the number the user asked for.
    return f"{bar}  {kept}/{total}{extra}"


def _bar_glyphs() -> tuple[str, str]:
    """Pick bar characters the stderr encoding can actually print."""

    # Capture's encoding can be missing in tests.
    encoding = getattr(sys.stderr, "encoding", None) or "utf-8"

    # Solid and empty blocks. Fall back when the stream is ASCII.
    try:
        "█░".encode(encoding)

    # ASCII terminals still get a readable track.
    except UnicodeEncodeError:
        # Hash and dash are the portable pair.
        return "#", "-"

    # Unicode track.
    return "█", "░"


class _Progress:
    """A bar that stays on screen for the whole crawl, including the wait."""

    def __init__(self, config: RunConfig):
        """Remember the run settings and that nothing has been drawn yet."""

        # Quiet and the article limit live here.
        self._config = config

        # Latest counts. The spinner thread reads these.
        self._kept = 0

        # Same, for ids already stored.
        self._skipped = 0

        # Which spinner glyph to show while a request is in flight.
        self._tick = 0

        # True after the first visible line, so the next paint rewrites it.
        self._drawn = False

        # Stops the spinner thread.
        self._stop = threading.Event()

        # Keeps the spinner and the main thread from writing the same line.
        self._lock = threading.Lock()

        # None until start() on a real terminal.
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Paint 0/limit immediately, then keep the line alive during fetches."""

        # The empty bar has to exist before the first request blocks.
        self.update(kept=0, skipped=0)

        # Pipes and `--quiet` do not get a background redraw.
        if not self._live():
            # The summary is enough there.
            return

        # Daemon so a crash cannot leave the process hanging on the spinner.
        self._thread = threading.Thread(target=self._spin, name="avherald-progress", daemon=True)

        # Redraws while get() is blocked on the network or the delay.
        self._thread.start()

    def _live(self) -> bool:
        """True when a live bar should take the terminal."""

        # `--quiet` owns silence.
        if self._config.quiet:
            # No bar, no spinner.
            return False

        # A captured stderr would only show the line after the crawl ends.
        return bool(getattr(sys.stderr, "isatty", lambda: False)())

    def _spin(self) -> None:
        """Redraw about seven times a second until the crawl stops."""

        # wait() returns True when close() sets the event.
        while not self._stop.wait(0.15):
            # Next glyph, so a stalled count still looks alive.
            self._tick += 1

            # Same numbers, new spinner.
            self._paint()

    def update(self, *, kept: int, skipped: int) -> None:
        """Store the latest counts and redraw if this is a terminal."""

        # The spinner thread will pick these up on its next tick too.
        self._kept = kept

        # Stored ids that did not count toward the limit.
        self._skipped = skipped

        # Paint now so a finished page does not wait for the next tick.
        self._paint()

    def _paint(self) -> None:
        """Write one bar line. Later paints replace that same line."""

        # Quiet runs never touch stderr.
        if self._config.quiet or not self._live():
            # Tests and pipes stay clean.
            return

        # The track plus kept/limit.
        line = render_progress(
            kept=self._kept,
            limit=self._config.limit,
            skipped=self._skipped,
        )

        # A moving mark while the fill itself has not changed.
        mark = "|/-\\"[self._tick % 4]

        # One visible row.
        text = f"{mark} {line}"

        # The spinner and update() can fire together.
        with self._lock:
            # First line must end in a newline or some consoles hide it until the end.
            if self._drawn:
                # Up one row, clear it, draw again with a newline so the console flushes.
                sys.stderr.write(f"\x1b[1A\x1b[2K{text}\n")

            # Nothing is on screen yet.
            else:
                # A real newline is what makes the bar show up before the crawl finishes.
                sys.stderr.write(f"{text}\n")

                # Later paints rewrite this row instead of stacking.
                self._drawn = True

            # Do not wait for the process to exit.
            sys.stderr.flush()

    def close(self) -> None:
        """Stop the spinner and leave the last bar line where it is."""

        # The loop exits on the next wait.
        self._stop.set()

        # No thread when this was quiet or not a terminal.
        if self._thread is not None:
            # Bound the wait so a stuck redraw cannot hold the process.
            self._thread.join(timeout=1)

            # close() can run twice from the finally block.
            self._thread = None


# Walk pages until the limit, the page cap, or the end of the list.
def _crawl(
        fetcher: HtmlFetcher,
        *,
        config: RunConfig,
        db: Database | None,
        progress: _Progress,
) -> _Crawl:
    """Download list pages and collect rows that still count toward the limit."""

    # Ids already in SQLite. Empty when there is no database.
    known = db.article_ids() if db is not None else set()

    # Grows as we keep rows, so a later page can't add the same id again.
    seen = set(known)

    # Empty means "every category".
    wanted = set(config.categories)

    # The rows this run will keep, in the order we saw them.
    collected: list[ArticleRecord] = []

    # Bumped once per successful download.
    pages_fetched = 0

    # Bumped by however many rows the parser returned.
    parsed = 0

    # Already-stored ids. These do not count toward the limit.
    skipped = 0

    # Wrong category. These don't count either.
    filtered = 0

    # Updated each time we keep a row.
    last_article_id: str | None = None

    # url is where we start. resumed_from is set only when a bookmark was used.
    url, resumed_from, incremental = _start_url(config, db)

    # If we stop in the middle of a page, this is rewritten to stay on it.
    resume_url = url

    # Flipped when there is no next page, or when an incremental run is caught up.
    completed = False

    # Empty bar first, so the wait for the first page is visible.
    progress.start()

    # Stop at the limit even if more pages exist.
    while url and len(collected) < config.limit:
        # `--pages` is an extra cap on top of the article limit.
        if config.max_pages is not None and pages_fetched >= config.max_pages:
            # Leave resume_url pointing at the page we did not fetch.
            break

        # Raises BlockedError when the site returns the ban page.
        html = fetcher.get(url)

        # Count the page only after it actually came back.
        pages_fetched += 1

        # next_url is None on the last page.
        rows, next_url = parse_list_page(html, source_page=url, base_url=config.base_url)

        # Includes rows we may skip or filter below.
        parsed += len(rows)

        # New ids kept from this page. Used by the incremental stop.
        new_on_page = 0

        # Stored ids seen on this page. Also used by that stop.
        known_on_page = 0

        # Set when the limit is hit before the page is finished.
        stopped_mid = False

        # index is needed so we can look at the rows we haven't consumed yet.
        for index, row in enumerate(rows):
            # Already stored, or already kept earlier in this run.
            if row.article_id in seen:
                # Does not count toward `--limit`.
                skipped += 1

                # The incremental check uses this.
                known_on_page += 1

                # Move to the next row on this page.
                continue

            # An empty wanted set means the category filter is off.
            if wanted and row.category not in wanted:
                # Dropped before it can become a kept row.
                filtered += 1

                # Still not a duplicate. Just the wrong category.
                continue

            # Claim the id so a later page can't collect it again.
            seen.add(row.article_id)

            # This one counts toward the limit.
            collected.append(row)

            # Fill the bar as rows are accepted, not only after the page ends.
            progress.update(kept=len(collected), skipped=skipped)

            # The bookmark records the last id we actually kept.
            last_article_id = row.article_id

            # Incremental mode treats a page of only-new rows as "keep going".
            new_on_page += 1

            # The limit can fall in the middle of a page.
            if len(collected) >= config.limit:
                # Rows after this one on the same page.
                remaining = rows[index + 1:]

                # If one of those would also have been kept, stay on this URL.
                has_more_unknown = any(
                    item.article_id not in seen
                    and (not wanted or item.category in wanted)
                    for item in remaining
                )

                # Stay put when this page still has work. Otherwise follow Next.
                resume_url = url if has_more_unknown else next_url

                # No resume URL means we have reached the end.
                completed = resume_url is None

                # Don't let the code below advance to the next page.
                stopped_mid = True

                # The limit is filled.
                break

        # Move the bar. Quiet runs and pipes ignore this.
        progress.update(kept=len(collected), skipped=skipped)

        # The while-loop also has to stop. `break` above only left the for-loop.
        if stopped_mid:
            # resume_url was chosen just above.
            break

        # A finished crawl that is run again stops when it hits known ids.
        if incremental and (known_on_page > 0 or new_on_page == 0):
            # Nothing to resume. The next fresh-looking run starts at the top.
            resume_url = None

            # Mark the bookmark complete so the next run uses incremental mode.
            completed = True

            # Don't keep paging through history we already stored.
            break

        # Follow the Next control. We do not build the offset ourselves.
        url = next_url

        # If we exit because url became None, this is the value we save.
        resume_url = url

        # Last page.
        if url is None:
            # The bookmark can say this filter is done.
            completed = True

    # The caller writes this, or throws it away on a dry run.
    return _Crawl(
        records=collected,
        pages_fetched=pages_fetched,
        parsed=parsed,
        skipped=skipped,
        filtered=filtered,
        resume_url=resume_url,
        last_article_id=last_article_id,
        completed=completed,
        resumed_from=resumed_from,
    )


# Choose the opening URL, and whether this run should stop at the first known id.
def _start_url(
        config: RunConfig, db: Database | None
) -> tuple[str, str | None, bool]:
    """Pick the first URL, and whether this run is just checking for new rows.

    The third value is the incremental flag. It is true only when the previous
    run for this filter said it had finished the list.
    """

    # Homepage, or the filtered list URL, unless --start-url was set.
    start = config.resolved_start_url()

    # No database, resume turned off, or --fresh: always the first page.
    if db is None or not config.resume or config.fresh:
        # Not a resume, and not an incremental catch-up.
        return start, None, False

    # Look up the bookmark for this exact sort and category mix.
    checkpoint = db.get_checkpoint(config.crawl_key())

    # First time we've crawled this combination.
    if checkpoint is None:
        # Start at the top.
        return start, None, False

    # The previous run reached the end. Start over, but stop at the first known id.
    if checkpoint.completed:
        # The True is the incremental flag.
        return start, None, True

    # A partial run saved the next page to open.
    if checkpoint.resume_url:
        # resumed_from is that same URL, so the summary can mention it.
        return checkpoint.resume_url, checkpoint.resume_url, False

    # A bookmark with no URL and not marked complete. Start over quietly.
    return start, None, False
