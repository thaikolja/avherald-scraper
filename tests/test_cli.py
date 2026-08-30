import pytest

from avherald_scraper.cli import build_parser, main
from avherald_scraper.config import load_config


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


def test_parser_accepts_fresh_and_resume_flags():
    args = build_parser().parse_args(["--fresh", "--no-resume"])
    assert args.fresh is True
    assert args.resume is False
