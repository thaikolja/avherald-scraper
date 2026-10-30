from pathlib import Path

import pytest

from avherald_scraper.config import load_config, parse_categories


def test_parse_categories_accepts_csv_and_repeats():
    assert parse_categories(["incident,accident", "news"]) == (
        "incident",
        "accident",
        "news",
    )


def test_parse_proxies_keeps_order_and_splits_commas():
    from avherald_scraper.config import parse_proxies

    assert parse_proxies("http://a:1, http://b:2") == ("http://a:1", "http://b:2")
    assert parse_proxies(["http://a:1", "http://b:2,http://a:1"]) == (
        "http://a:1",
        "http://b:2",
    )


def test_parse_categories_rejects_unknown():
    with pytest.raises(ValueError, match="unknown category"):
        parse_categories(["banana"])


def test_load_config_cli_overrides_ini(tmp_path: Path):
    (tmp_path / "config.ini").write_text(
        """
[crawl]
limit = 10
sort = occurrence
categories = crash
verbose = true

[network]
delay = 9
""",
        encoding="utf-8",
    )
    config = load_config(
        cli={"limit": 50, "delay": None, "categories": ["incident"]},
        cwd=tmp_path,
    )
    assert config.limit == 50
    assert config.delay == 9
    assert config.sort == "occurrence"
    assert config.categories == ("incident",)
    assert config.verbose is True
    assert config.resolved_start_url() == "https://avherald.com/h?list=&opt=1025"


def test_config_ini_values_and_cli_override(tmp_path: Path):
    (tmp_path / "config.ini").write_text(
        """
[crawl]
limit = 10
sort = occurrence
resume = false

[network]
delay = 9
""",
        encoding="utf-8",
    )
    from_file = load_config(cwd=tmp_path)
    assert from_file.limit == 10
    assert from_file.sort == "occurrence"
    assert from_file.resume is False
    assert from_file.delay == 9.0

    from_cli = load_config(cli={"limit": 3, "sort": "update"}, cwd=tmp_path)
    assert from_cli.limit == 3
    assert from_cli.sort == "update"
    assert from_cli.delay == 9.0
    assert from_cli.resume is False


def test_shipped_config_ini_matches_documented_defaults():
    root = Path(__file__).resolve().parents[1]
    config = load_config(cwd=root)
    assert config.base_url == "https://avherald.com"
    assert config.database_path == Path("./data/avherald.sqlite")
    assert config.limit == 10
    assert config.sort == "update"
    assert config.categories == ()
    assert config.max_pages is None
    assert config.resume is True
    assert config.fresh is False
    assert config.dry_run is False
    assert config.verbose is False
    assert config.delay == 3.0
    assert config.timeout == 20.0
    assert config.proxies == ()

    overridden = load_config(cli={"limit": 7, "sort": "occurrence"}, cwd=root)
    assert overridden.limit == 7
    assert overridden.sort == "occurrence"


def test_ini_resume_and_fresh(tmp_path: Path):
    (tmp_path / "config.ini").write_text(
        """
[crawl]
resume = false
fresh = true
limit = 25
""",
        encoding="utf-8",
    )
    config = load_config(cwd=tmp_path)
    assert config.resume is False
    assert config.fresh is True
    assert config.limit == 25
