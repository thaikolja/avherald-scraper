from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from avherald_scraper.models import ArticleRecord

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


@dataclass(frozen=True)
class Checkpoint:
    crawl_key: str
    resume_url: str | None
    last_article_id: str | None
    completed: bool


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def init(self) -> None:
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> Database:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) FROM articles").fetchone()
        return int(row[0])

    def article_ids(self) -> set[str]:
        rows = self.conn.execute("SELECT article_id FROM articles")
        return {str(row[0]) for row in rows}

    def get_checkpoint(self, crawl_key: str) -> Checkpoint | None:
        row = self.conn.execute(
            """
            SELECT crawl_key, resume_url, last_article_id, completed
            FROM crawl_state
            WHERE crawl_key = ?
            """,
            (crawl_key,),
        ).fetchone()
        if row is None:
            return None
        resume_url = row["resume_url"] or None
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
        timestamp = now or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
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
        self.conn.commit()

    def clear_checkpoint(self, crawl_key: str) -> None:
        self.conn.execute("DELETE FROM crawl_state WHERE crawl_key = ?", (crawl_key,))
        self.conn.commit()

    def upsert_many(
        self,
        records: list[ArticleRecord],
        *,
        now: str | None = None,
    ) -> tuple[int, int]:
        timestamp = now or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        inserted = 0
        updated = 0
        seen_in_batch: set[str] = set()
        for record in records:
            if record.article_id in seen_in_batch:
                continue
            seen_in_batch.add(record.article_id)
            if self._exists(record.article_id):
                self._update(record, timestamp)
                updated += 1
            else:
                self._insert(record, timestamp)
                inserted += 1
        self.conn.commit()
        return inserted, updated

    def _exists(self, article_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM articles WHERE article_id = ?",
            (article_id,),
        ).fetchone()
        return row is not None

    def _insert(self, record: ArticleRecord, timestamp: str) -> None:
        self.conn.execute(
            """
            INSERT INTO articles (
                article_id, url, heading, list_date, list_date_iso,
                icon, category, source_page, first_seen_at, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
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
            ),
        )

    def _update(self, record: ArticleRecord, timestamp: str) -> None:
        self.conn.execute(
            """
            UPDATE articles SET
                url = ?,
                heading = ?,
                list_date = ?,
                list_date_iso = ?,
                icon = ?,
                category = ?,
                source_page = ?,
                last_seen_at = ?
            WHERE article_id = ?
            """,
            (
                record.url,
                record.heading,
                record.list_date,
                record.list_date_iso,
                record.icon,
                record.category,
                record.source_page,
                timestamp,
                record.article_id,
            ),
        )
