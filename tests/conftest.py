from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def list_page_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "list_page.html").read_text(encoding="utf-8")


@pytest.fixture
def blocked_page_html(fixtures_dir: Path) -> str:
    return (fixtures_dir / "blocked_page.html").read_text(encoding="utf-8")
