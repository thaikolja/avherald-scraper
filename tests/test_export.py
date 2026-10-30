import csv
import json
import zipfile
from pathlib import Path

import pytest

from avherald_scraper.config import load_config
from avherald_scraper.db import Database
from avherald_scraper.export import export_articles
from avherald_scraper.models import ArticleRecord


def _record() -> ArticleRecord:
    return ArticleRecord(
        article_id="53f3f5aa",
        url="https://avherald.com/h?article=53f3f5aa",
        heading="ANZ, brakes & fault",
        list_date="Sunday Aug 30th 2026",
        list_date_iso="2026-08-30",
        icon="incident.gif",
        category="incident",
        source_page="https://avherald.com/",
    )


def _filled(tmp_path: Path) -> Database:
    db = Database(tmp_path / "avherald.sqlite")
    db.init()
    db.upsert_many([_record()], now="2026-08-30T12:00:00+00:00")
    return db


def test_export_json_and_csv(tmp_path: Path):
    db = _filled(tmp_path)
    json_path = export_articles(db, "json", db.path)
    csv_path = export_articles(db, "csv", db.path)
    db.close()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload[0]["heading"] == "ANZ, brakes & fault"
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["article_id"] == "53f3f5aa"
    assert rows[0]["heading"] == "ANZ, brakes & fault"


def test_export_xlsx_keeps_ampersand(tmp_path: Path):
    db = _filled(tmp_path)
    path = export_articles(db, "xlsx", db.path)
    db.close()
    with zipfile.ZipFile(path) as book:
        sheet = book.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "ANZ, brakes &amp; fault" in sheet
    assert "article_id" in sheet


def test_format_from_ini_and_cli(tmp_path: Path):
    (tmp_path / "config.ini").write_text("[storage]\nformat = json\n", encoding="utf-8")
    from_file = load_config(cwd=tmp_path)
    assert from_file.output_format == "json"
    from_cli = load_config(cli={"output_format": "csv"}, cwd=tmp_path)
    assert from_cli.output_format == "csv"


def test_unknown_format_is_rejected(tmp_path: Path):
    (tmp_path / "config.ini").write_text("[storage]\nformat = pages\n", encoding="utf-8")
    with pytest.raises(ValueError, match="format must be"):
        load_config(cwd=tmp_path)
