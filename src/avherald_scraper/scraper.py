from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from avherald_scraper.config import RunConfig
from avherald_scraper.db import Database
from avherald_scraper.http import Client
from avherald_scraper.models import ArticleRecord
from avherald_scraper.parser import parse_list_page


class HtmlFetcher(Protocol):
    def get(self, url: str) -> str: ...


@dataclass(frozen=True)
class ScrapeResult:
    pages_fetched: int
    parsed: int
    inserted: int
    updated: int
    stored: int
    skipped_duplicate: int
    filtered: int = 0
    records: tuple[ArticleRecord, ...] = ()
    resumed_from: str | None = None

    def category_counts(self) -> dict[str, int]:
        counts: Counter[str] = Counter(
            record.category or "unknown" for record in self.records
        )
        return dict(counts)


@dataclass
class _Crawl:
    records: list[ArticleRecord]
    pages_fetched: int
    parsed: int
    skipped: int
    filtered: int
    resume_url: str | None
    last_article_id: str | None
    completed: bool
    resumed_from: str | None


def run(config: RunConfig, *, client: HtmlFetcher | None = None) -> ScrapeResult:
    owned_client = False
    fetcher = client
    if fetcher is None:
        fetcher = Client(
            delay=config.delay,
            timeout=config.timeout,
            proxy=config.proxy,
            user_agent=config.user_agent,
        )
        owned_client = True

    db: Database | None = None
    path = Path(config.database_path)
    if not config.dry_run or path.exists():
        db = Database(path)
        db.init()
        if config.fresh and not config.dry_run:
            db.clear_checkpoint(config.crawl_key())

    try:
        crawl = _crawl(fetcher, config=config, db=db)
        inserted = updated = stored = 0
        if not config.dry_run and db is not None:
            inserted, updated = db.upsert_many(crawl.records)
            db.save_checkpoint(
                config.crawl_key(),
                resume_url=crawl.resume_url,
                last_article_id=crawl.last_article_id,
                completed=crawl.completed,
            )
            stored = db.count()
    finally:
        if db is not None:
            db.close()
        close = getattr(fetcher, "close", None)
        if owned_client and callable(close):
            close()

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
    if config.verbose:
        where = crawl.resumed_from or config.resolved_start_url()
        print(
            f"start={where} pages={crawl.pages_fetched} parsed={crawl.parsed} "
            f"kept={len(crawl.records)} inserted={inserted} updated={updated} "
            f"skipped_duplicate={crawl.skipped} filtered={crawl.filtered} "
            f"stored={stored}"
        )
    return result


def _crawl(
    fetcher: HtmlFetcher,
    *,
    config: RunConfig,
    db: Database | None,
) -> _Crawl:
    known = db.article_ids() if db is not None else set()
    seen = set(known)
    wanted = set(config.categories)
    collected: list[ArticleRecord] = []
    pages_fetched = 0
    parsed = 0
    skipped = 0
    filtered = 0
    last_article_id: str | None = None

    url, resumed_from, incremental = _start_url(config, db)
    resume_url = url
    completed = False

    while url and len(collected) < config.limit:
        if config.max_pages is not None and pages_fetched >= config.max_pages:
            break
        if config.verbose:
            print(f"Fetching {url}")
        html = fetcher.get(url)
        pages_fetched += 1
        rows, next_url = parse_list_page(html, source_page=url, base_url=config.base_url)
        parsed += len(rows)
        new_on_page = 0
        known_on_page = 0
        stopped_mid = False

        for index, row in enumerate(rows):
            if row.article_id in seen:
                skipped += 1
                known_on_page += 1
                continue
            if wanted and row.category not in wanted:
                filtered += 1
                continue
            seen.add(row.article_id)
            collected.append(row)
            last_article_id = row.article_id
            new_on_page += 1
            if len(collected) >= config.limit:
                remaining = rows[index + 1 :]
                has_more_unknown = any(
                    item.article_id not in seen
                    and (not wanted or item.category in wanted)
                    for item in remaining
                )
                resume_url = url if has_more_unknown else next_url
                completed = resume_url is None
                stopped_mid = True
                break

        if stopped_mid:
            break

        if incremental and (known_on_page > 0 or new_on_page == 0):
            resume_url = None
            completed = True
            break

        url = next_url
        resume_url = url
        if url is None:
            completed = True

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


def _start_url(
    config: RunConfig, db: Database | None
) -> tuple[str, str | None, bool]:
    start = config.resolved_start_url()
    if db is None or not config.resume or config.fresh:
        return start, None, False
    checkpoint = db.get_checkpoint(config.crawl_key())
    if checkpoint is None:
        return start, None, False
    if checkpoint.completed:
        return start, None, True
    if checkpoint.resume_url:
        return checkpoint.resume_url, checkpoint.resume_url, False
    return start, None, False
