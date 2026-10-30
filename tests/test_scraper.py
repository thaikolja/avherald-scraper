from pathlib import Path

from avherald_scraper.config import RunConfig
from avherald_scraper.scraper import render_progress, run

PAGE_ONE_NEXT = "https://avherald.com/h?list=&opt=0&offset=20260821192052%2B53e33032"


class ScriptedClient:
    def __init__(self, pages: dict[str, str]):
        self.pages = pages
        self.urls: list[str] = []

    def get(self, url: str) -> str:
        self.urls.append(url)
        return self.pages[url]


def _many_rows_html(count: int) -> str:
    rows = ['<table><tr><td>Sunday Aug 30th 2026</td></tr>']
    for i in range(count):
        article_id = f"{i:08x}"
        rows.append(
            f"""
            <tr>
              <td><img src="/images/incident.gif" alt="Incident"></td>
              <td>
                <a href="/h?article={article_id}&opt=0">
                  <span class="headline_avherald">Incident {article_id}</span>
                </a>
              </td>
            </tr>
            """
        )
    rows.append("</table>")
    return "".join(rows)


def test_scrape_follows_next_and_stores_all_rows(
    tmp_path: Path, list_page_html: str, fixtures_dir: Path
):
    page_two = (fixtures_dir / "list_page_2.html").read_text(encoding="utf-8")
    client = ScriptedClient(
        {
            "https://avherald.com/": list_page_html,
            PAGE_ONE_NEXT: page_two,
        }
    )
    db_path = tmp_path / "avherald.sqlite"
    result = run(
        RunConfig(limit=50, database_path=db_path, start_url="https://avherald.com/"),
        client=client,
    )
    assert client.urls == ["https://avherald.com/", PAGE_ONE_NEXT]
    assert result.pages_fetched == 2
    assert result.parsed == 3
    assert result.inserted == 3
    assert result.updated == 0
    assert result.stored == 3


def test_scrape_stops_at_limit_without_fetching_next(
    tmp_path: Path, list_page_html: str, fixtures_dir: Path
):
    page_two = (fixtures_dir / "list_page_2.html").read_text(encoding="utf-8")
    client = ScriptedClient(
        {
            "https://avherald.com/": list_page_html,
            PAGE_ONE_NEXT: page_two,
        }
    )
    result = run(
        RunConfig(limit=2, database_path=tmp_path / "avherald.sqlite", start_url="https://avherald.com/"),
        client=client,
    )
    assert client.urls == ["https://avherald.com/"]
    assert result.stored == 2
    assert result.inserted == 2


def test_scrape_truncates_a_page_that_exceeds_limit(tmp_path: Path):
    client = ScriptedClient({"https://avherald.com/": _many_rows_html(60)})
    result = run(
        RunConfig(limit=50, database_path=tmp_path / "avherald.sqlite", start_url="https://avherald.com/"),
        client=client,
    )
    assert result.pages_fetched == 1
    assert result.stored == 50
    assert result.inserted == 50


def test_scrape_keeps_only_requested_categories(
    tmp_path: Path, list_page_html: str, fixtures_dir: Path
):
    page_two = (fixtures_dir / "list_page_2.html").read_text(encoding="utf-8")
    client = ScriptedClient(
        {
            "https://avherald.com/": list_page_html,
            PAGE_ONE_NEXT: page_two,
        }
    )
    result = run(
        RunConfig(
            limit=50,
            database_path=tmp_path / "avherald.sqlite",
            start_url="https://avherald.com/",
            categories=("incident",),
        ),
        client=client,
    )
    assert result.inserted == 2
    assert result.filtered == 1
    assert client.urls == ["https://avherald.com/", PAGE_ONE_NEXT]


def test_scrape_stops_after_max_pages(tmp_path: Path, list_page_html: str, fixtures_dir: Path):
    page_two = (fixtures_dir / "list_page_2.html").read_text(encoding="utf-8")
    client = ScriptedClient(
        {
            "https://avherald.com/": list_page_html,
            PAGE_ONE_NEXT: page_two,
        }
    )
    result = run(
        RunConfig(
            limit=50,
            max_pages=1,
            database_path=tmp_path / "avherald.sqlite",
            start_url="https://avherald.com/",
        ),
        client=client,
    )
    assert client.urls == ["https://avherald.com/"]
    assert result.pages_fetched == 1
    assert result.inserted == 2


def test_second_run_skips_stored_ids_and_continues(tmp_path: Path):
    db_path = tmp_path / "avherald.sqlite"
    html = _many_rows_html(6)
    pages = {"https://avherald.com/": html}
    first = run(
        RunConfig(limit=2, database_path=db_path, start_url="https://avherald.com/"),
        client=ScriptedClient(pages),
    )
    assert [row.article_id for row in first.records] == ["00000000", "00000001"]
    assert first.stored == 2

    second = run(
        RunConfig(limit=2, database_path=db_path, start_url="https://avherald.com/"),
        client=ScriptedClient(pages),
    )
    assert [row.article_id for row in second.records] == ["00000002", "00000003"]
    assert second.inserted == 2
    assert second.stored == 4
    assert second.skipped_duplicate >= 2


def test_second_run_resumes_on_the_next_page(
    tmp_path: Path, list_page_html: str, fixtures_dir: Path
):
    db_path = tmp_path / "avherald.sqlite"
    page_two = (fixtures_dir / "list_page_2.html").read_text(encoding="utf-8")
    pages = {
        "https://avherald.com/": list_page_html,
        PAGE_ONE_NEXT: page_two,
    }
    first = run(
        RunConfig(limit=2, database_path=db_path, start_url="https://avherald.com/"),
        client=ScriptedClient(pages),
    )
    assert first.inserted == 2
    second_client = ScriptedClient(pages)
    second = run(
        RunConfig(limit=2, database_path=db_path, start_url="https://avherald.com/"),
        client=second_client,
    )
    assert second_client.urls == [PAGE_ONE_NEXT]
    assert [row.article_id for row in second.records] == ["53e33032"]
    assert second.stored == 3


def test_fresh_starts_from_the_first_page_again(
    tmp_path: Path, list_page_html: str, fixtures_dir: Path
):
    db_path = tmp_path / "avherald.sqlite"
    page_two = (fixtures_dir / "list_page_2.html").read_text(encoding="utf-8")
    pages = {
        "https://avherald.com/": list_page_html,
        PAGE_ONE_NEXT: page_two,
    }
    run(
        RunConfig(limit=2, database_path=db_path, start_url="https://avherald.com/"),
        client=ScriptedClient(pages),
    )
    client = ScriptedClient(pages)
    run(
        RunConfig(
            limit=2,
            database_path=db_path,
            start_url="https://avherald.com/",
            fresh=True,
        ),
        client=client,
    )
    assert client.urls[0] == "https://avherald.com/"


def test_dry_run_does_not_write_database(tmp_path: Path, list_page_html: str):
    db_path = tmp_path / "avherald.sqlite"
    client = ScriptedClient({"https://avherald.com/": list_page_html})
    result = run(
        RunConfig(
            limit=50,
            max_pages=1,
            database_path=db_path,
            start_url="https://avherald.com/",
            dry_run=True,
        ),
        client=client,
    )
    assert result.inserted == 0
    assert result.stored == 0
    assert len(result.records) == 2
    assert not db_path.exists()


def test_render_progress_tracks_the_limit():
    line = render_progress(kept=5, limit=10, skipped=2, width=10)
    track, count, skipped = line.split("  ")
    assert len(track) == 10
    assert count == "5/10"
    assert skipped == "skipped 2"
    quiet = render_progress(kept=0, limit=10, skipped=0, width=10)
    assert "skipped" not in quiet
    assert quiet.endswith("0/10")
