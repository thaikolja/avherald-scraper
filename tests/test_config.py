from pathlib import Path

import pytest

from avherald_scraper.config import RunConfig, load_config, parse_categories


def test_parse_categories_accepts_csv_and_repeats():
    assert parse_categories(["incident,accident", "news"]) == (
        "incident",
        "accident",
        "news",
    )


def test_parse_categories_rejects_unknown():
    with pytest.raises(ValueError, match="unknown category"):
        parse_categories(["banana"])


def test_load_config_cli_overrides_toml(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "avherald.toml").write_text(
        """
limit = 10
delay = 9
sort = "occurrence"
categories = ["crash"]
verbose = true
""",
        encoding="utf-8",
    )
    config = load_config(
        cli={"limit": 50, "delay": None, "categories": ["incident"]},
        environ={},
    )
    assert config.limit == 50
    assert config.delay == 9
    assert config.sort == "occurrence"
    assert config.categories == ("incident",)
    assert config.verbose is True
    assert config.resolved_start_url() == "https://avherald.com/h?list=&opt=1025"


def test_env_resume_and_fresh(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = load_config(
        environ={
            "AVHERALD_RESUME": "false",
            "AVHERALD_FRESH": "true",
            "AVHERALD_LIMIT": "25",
        }
    )
    assert config.resume is False
    assert config.fresh is True
    assert config.limit == 25
