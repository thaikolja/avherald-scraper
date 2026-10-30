import pytest

from avherald_scraper.cli import _format_cli_records, build_parser, main
from avherald_scraper.config import load_config
from avherald_scraper.models import ArticleRecord
from avherald_scraper.scraper import ScrapeResult


def test_cli_help_exits_zero():
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_parser_defaults_are_unset_so_config_can_fill_them():
    args = build_parser().parse_args([])
    assert args.limit is None
    assert args.verbose is None
    assert args.categories is None


def test_parser_accepts_limit_and_db(tmp_path):
    args = build_parser().parse_args(["--limit", "50", "--db", str(tmp_path / "x.sqlite")])
    assert args.limit == 50
    assert args.database_path.name == "x.sqlite"


def test_short_flags_and_repeatable_categories(tmp_path):
    args = build_parser().parse_args(
        ["-n", "20", "-c", "incident,accident", "-c", "news", "-o", str(tmp_path / "out.sqlite"), "-v"]
    )
    assert args.limit == 20
    assert args.categories == ["incident,accident", "news"]
    assert args.verbose is True
    config = load_config(
        cli={
            "limit": args.limit,
            "categories": args.categories,
            "verbose": args.verbose,
            "database_path": args.database_path,
        }
    )
    assert config.categories == ("incident", "accident", "news")
    assert config.limit == 20


def test_main_rejects_unknown_category():
    assert main(["-c", "spaceship"]) == 2


def test_show_config_exits_without_writing_database(tmp_path, capsys):
    ini = tmp_path / "custom.ini"
    ini.write_text(
        "[crawl]\nlimit = 4\nsort = occurrence\n",
        encoding="utf-8",
    )
    code = main(["--show-config", "--config", str(ini), "--limit", "9"])
    assert code == 0
    out = capsys.readouterr().out
    assert "limit: 9" in out
    assert "sort: occurrence" in out
    assert "proxy: direct" in out
    assert str(ini) in out
    assert list(tmp_path.glob("*.sqlite")) == []


def test_cli_format_spaces_each_headline():
    result = ScrapeResult(
        pages_fetched=1,
        parsed=1,
        inserted=1,
        updated=0,
        stored=1,
        skipped_duplicate=0,
        records=(
            ArticleRecord(
                article_id="53f3f5aa",
                url="https://avherald.com/h?article=53f3f5aa",
                heading="ANZ brakes fault",
                list_date=None,
                list_date_iso="2026-08-30",
                icon="incident.gif",
                category="incident",
                source_page="https://avherald.com/",
            ),
        ),
    )
    text = _format_cli_records(result)
    assert text.startswith("1\n")
    assert "\n\n    incident    2026-08-30\n\n    ANZ brakes fault\n\n    https://" in text


def test_help_points_at_config_ini_for_defaults():
    parser = build_parser()
    help_text = parser.format_help()
    assert "config.ini, else 50" in help_text
    assert "config.ini, else" in help_text


def test_parser_accepts_fresh_and_resume_flags():
    args = build_parser().parse_args(["--fresh", "--no-resume"])
    assert args.fresh is True
    assert args.resume is False
