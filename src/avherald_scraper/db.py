"""SQLite storage for headline rows and the crawl bookmark.

`article_id` is the primary key. Seeing the same id again updates the
headline fields and leaves `first_seen_at` alone. `crawl_state` remembers
which list page to open next time.
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

# Annotations refer to names defined later in the file.
from __future__ import annotations

# The standard-library driver. There is no separate database dependency.
import sqlite3

# Checkpoint is a small frozen snapshot of one crawl_state row.
from dataclasses import dataclass

# Timestamps are UTC, stored as text.
from datetime import UTC, datetime

# Callers pass either a string path or a pathlib path.
from pathlib import Path

# `__enter__` returns this object, including a subclass.
from typing import Self

# The row shape written into the articles table.
from avherald_scraper.models import ArticleRecord

# Created on first open. Running it twice is harmless.
SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    article_id     TEXT PRIMARY KEY,
    url            TEXT NOT NULL UNIQUE,
    heading        TEXT NOT NULL,
    list_date      TEXT,
    list_date_iso  TEXT,
    icon           TEXT,
    category       TEXT,
    source_page    TEXT,
    first_seen_at  TEXT NOT NULL,
    last_seen_at   TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_article_id ON articles(article_id);

CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
CREATE INDEX IF NOT EXISTS idx_articles_list_date ON articles(list_date_iso);

CREATE TABLE IF NOT EXISTS crawl_state (
    crawl_key        TEXT PRIMARY KEY,
    resume_url       TEXT,
    last_article_id  TEXT,
    completed        INTEGER NOT NULL DEFAULT 0,
    updated_at       TEXT NOT NULL
);
"""


# One saved position, detached from the live database connection.
@dataclass(frozen=True)
class Checkpoint:
    """The bookmark for a single sort-and-category crawl."""

    # `update|*` or `url|...|*`, from RunConfig.crawl_key.
    crawl_key: str

    # List page to open next. Empty once the crawl has caught up.
    resume_url: str | None

    # Last new id kept on the previous run. Informational.
    last_article_id: str | None

    # True when the previous run decided there was nothing new left.
    completed: bool


class Database:
    """A connection to one SQLite file, plus the few queries the crawl needs."""

    def __init__(self, path: str | Path):
        """Open the file, creating the parent folder when it is missing."""

        # Store a Path so later calls don't care what the caller passed.
        self.path = Path(path)

        # `data/` is not created by the installer. Make it on first use.
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # One connection for the whole run. The crawl is single-threaded.
        self.conn = sqlite3.connect(self.path)

        # Rows come back as mappings, so columns can be read by name.
        self.conn.row_factory = sqlite3.Row

        # Cheap insurance. This schema doesn't use foreign keys today.
        self.conn.execute("PRAGMA foreign_keys = ON")

        # Wait instead of failing when another process has the file open.
        self.conn.execute("PRAGMA busy_timeout = 5000")

    def init(self) -> None:
        """Create the tables and indexes if this file is new."""

        # Readers don't block writers. Fetch the result so the pragma finishes.
        self.conn.execute("PRAGMA journal_mode = WAL").fetchone()

        # The script is idempotent, so an existing database just gets migrated
        # forward by the IF NOT EXISTS clauses.
        self.conn.executescript(SCHEMA)

        # executescript does not always leave the transaction the way we want.
        self.conn.commit()

    def close(self) -> None:
        """Close the connection."""

        # Further calls on this object will fail, which is what we want.
        self.conn.close()

    def __enter__(self) -> Self:
        """Support `with Database(path) as db`."""

        # `__init__` already opened the file.
        return self

    def __exit__(self, *exc: object) -> None:
        """Close the connection when the `with` block ends."""

        # Don't swallow the exception. Just release the file.
        self.close()

    def count(self) -> int:
        """Return how many article rows are stored."""

        # One number. The table is small enough that COUNT(*) is fine.
        row = self.conn.execute("SELECT COUNT(*) FROM articles").fetchone()

        # fetchone() is a row here, not None, because the query always returns.
        return int(row[0])

    def article_ids(self) -> set[str]:
        """Return every stored id, so the crawl can skip them."""

        # A set makes the "have we seen this?" check cheap while paging.
        rows = self.conn.execute("SELECT article_id FROM articles")

        # Coerce to str in case a driver ever hands the value back oddly.
        return {str(row[0]) for row in rows}

    def get_checkpoint(self, crawl_key: str) -> Checkpoint | None:
        """Load the bookmark for this crawl key, or None if this is a first run."""

        # One row per key. The key includes the sort and the category filter.
        row = self.conn.execute(
            """
            SELECT crawl_key, resume_url, last_article_id, completed
            FROM crawl_state
            WHERE crawl_key = ?
            """,
            (crawl_key,),
        ).fetchone()

        # No row yet means we start from the first list page.
        if row is None:
            # The caller treats None as "no bookmark".
            return None

        # An empty string in the column is the same as "no URL" for us.
        resume_url = row["resume_url"] or None

        # completed is stored as 0/1. Bool keeps the rest of the code readable.
        return Checkpoint(
            crawl_key=row["crawl_key"],
            resume_url=resume_url,
            last_article_id=row["last_article_id"],
            completed=bool(row["completed"]),
        )

    def save_checkpoint(
            self,
            crawl_key: str,
            *,
            resume_url: str | None,
            last_article_id: str | None,
            completed: bool,
            now: str | None = None,
    ) -> None:
        """Insert or replace the bookmark for this crawl key."""

        # Tests pass `now` so the timestamp doesn't depend on the clock.
        timestamp = now or datetime.now(UTC).replace(microsecond=0).isoformat()

        # Upsert on the key. A second run overwrites the previous bookmark.
        self.conn.execute(
            """
            INSERT INTO crawl_state (
                crawl_key, resume_url, last_article_id, completed, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(crawl_key) DO UPDATE SET
                resume_url = excluded.resume_url,
                last_article_id = excluded.last_article_id,
                completed = excluded.completed,
                updated_at = excluded.updated_at
            """,
            (
                crawl_key,
                resume_url,
                last_article_id,
                1 if completed else 0,
                timestamp,
            ),
        )

        # The crawl can be killed after this and still resume.
        self.conn.commit()

    def clear_checkpoint(self, crawl_key: str) -> None:
        """Forget the bookmark so the next page walk starts at the top."""

        # Other crawl keys (a different category filter, for example) stay put.
        self.conn.execute("DELETE FROM crawl_state WHERE crawl_key = ?", (crawl_key,))

        # Don't leave the delete sitting in a transaction.
        self.conn.commit()

    def upsert_many(
            self,
            records: list[ArticleRecord],
            *,
            now: str | None = None,
    ) -> tuple[int, int]:
        """Insert new rows and refresh rows we already have.

        Returns `(inserted, updated)`.
        """

        # Nothing to write. Skip the id lookup.
        if not records:
            # The caller still expects a pair of counts.
            return 0, 0

        # One timestamp for the whole batch, so a run shares a last_seen_at.
        timestamp = now or datetime.now(UTC).replace(microsecond=0).isoformat()

        # One read for the whole batch, not one SELECT per row.
        known = self.article_ids()

        # Counted separately so the CLI can print both numbers.
        inserted = 0

        # An update still counts as work, but it is not a new article.
        updated = 0

        # The same id can appear twice in one batch. Keep the first copy.
        seen_in_batch: set[str] = set()

        # Bound rows for the single executemany below.
        rows: list[tuple] = []

        # Order matches the listing, which is the order the crawl collected.
        for record in records:
            # A duplicate inside this batch would just write the same row twice.
            if record.article_id in seen_in_batch:
                # Skip it. It is not an insert and not an update.
                continue

            # Remember it before we count it.
            seen_in_batch.add(record.article_id)

            # Already stored. The conflict clause will refresh it.
            if record.article_id in known:
                # Tell the summary this was a refresh.
                updated += 1

            # New id.
            else:
                # Tell the summary this was new.
                inserted += 1

            # first_seen_at is inserted only. The conflict update leaves it alone.
            rows.append(
                (
                    record.article_id,
                    record.url,
                    record.heading,
                    record.list_date,
                    record.list_date_iso,
                    record.icon,
                    record.category,
                    record.source_page,
                    timestamp,
                    timestamp,
                )
            )

        # One statement for the batch. Conflict keeps the original first_seen_at.
        self.conn.executemany(
            """
            INSERT INTO articles (
                article_id, url, heading, list_date, list_date_iso,
                icon, category, source_page, first_seen_at, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(article_id) DO UPDATE SET
                url = excluded.url,
                heading = excluded.heading,
                list_date = excluded.list_date,
                list_date_iso = excluded.list_date_iso,
                icon = excluded.icon,
                category = excluded.category,
                source_page = excluded.source_page,
                last_seen_at = excluded.last_seen_at
            """,
            rows,
        )

        # One commit for the batch, not one per row.
        self.conn.commit()

        # The crawl report prints these.
        return inserted, updated
