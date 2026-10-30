from pathlib import Path

from avherald_scraper.db import Database
from avherald_scraper.models import ArticleRecord


def _record(**overrides) -> ArticleRecord:
    data = {
        "article_id": "53f3f5aa",
        "url": "https://avherald.com/h?article=53f3f5aa",
        "heading": "ANZ B789 at Auckland on Apr 25th 2026, brakes fault on line up",
        "list_date": "Sunday Aug 30th 2026",
        "list_date_iso": "2026-08-30",
        "icon": "incident.gif",
        "category": "incident",
        "source_page": "https://avherald.com/",
    }
    data.update(overrides)
    return ArticleRecord(**data)


def test_init_creates_articles_table(tmp_path: Path):
    db = Database(tmp_path / "avherald.sqlite")
    db.init()
    names = {
        row[0]
        for row in db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert "articles" in names
    db.close()


def test_upsert_inserts_two_records(tmp_path: Path):
    db = Database(tmp_path / "avherald.sqlite")
    db.init()
    inserted, updated = db.upsert_many(
        [
            _record(),
            _record(
                article_id="53ef846a",
                url="https://avherald.com/h?article=53ef846a",
                heading="American B738 at Las Vegas",
            ),
        ],
        now="2026-08-30T12:00:00+00:00",
    )
    assert inserted == 2
    assert updated == 0
    assert db.count() == 2
    db.close()


def test_same_article_id_never_creates_a_second_row(tmp_path: Path):
    db = Database(tmp_path / "avherald.sqlite")
    db.init()
    db.upsert_many([_record(), _record(heading="changed")])
    assert db.count() == 1
    assert db.article_ids() == {"53f3f5aa"}
    db.close()


def test_checkpoint_roundtrip(tmp_path: Path):
    db = Database(tmp_path / "avherald.sqlite")
    db.init()
    assert db.get_checkpoint("update|*") is None
    db.save_checkpoint(
        "update|*",
        resume_url="https://avherald.com/h?list=&opt=0&offset=1",
        last_article_id="53f3f5aa",
        completed=False,
        now="2026-08-31T00:00:00+00:00",
    )
    row = db.get_checkpoint("update|*")
    assert row is not None
    assert row.resume_url.endswith("offset=1")
    assert row.last_article_id == "53f3f5aa"
    assert row.completed is False
    db.clear_checkpoint("update|*")
    assert db.get_checkpoint("update|*") is None
    db.close()


def test_upsert_updates_existing_and_keeps_first_seen(tmp_path: Path):
    db = Database(tmp_path / "avherald.sqlite")
    db.init()
    db.upsert_many([_record()], now="2026-08-30T12:00:00+00:00")
    inserted, updated = db.upsert_many(
        [_record(heading="ANZ B789 at Auckland, updated heading")],
        now="2026-08-31T09:00:00+00:00",
    )
    assert inserted == 0
    assert updated == 1
    assert db.count() == 1
    row = db.conn.execute(
        "SELECT heading, first_seen_at, last_seen_at FROM articles WHERE article_id = ?",
        ("53f3f5aa",),
    ).fetchone()
    assert row["heading"] == "ANZ B789 at Auckland, updated heading"
    assert row["first_seen_at"] == "2026-08-30T12:00:00+00:00"
    assert row["last_seen_at"] == "2026-08-31T09:00:00+00:00"
    db.close()
