from avherald_scraper.parser import is_blocked, parse_list_page


def test_is_blocked_detects_ip_ban_page(blocked_page_html: str, list_page_html: str):
    assert is_blocked(blocked_page_html) is True
    assert is_blocked(list_page_html) is False


def test_parse_list_page_extracts_listing_rows_not_footer(list_page_html: str):
    records, next_url = parse_list_page(
        list_page_html,
        source_page="https://avherald.com/",
    )
    assert [row.article_id for row in records] == ["53f3f5aa", "53ef846a"]
    assert all(row.source_page == "https://avherald.com/" for row in records)


def test_parse_list_page_captures_heading_date_and_icon(list_page_html: str):
    records, _ = parse_list_page(list_page_html, source_page="https://avherald.com/")
    first = records[0]
    assert first.article_id == "53f3f5aa"
    assert first.url == "https://avherald.com/h?article=53f3f5aa"
    assert first.heading == "ANZ B789 at Auckland on Apr 25th 2026, brakes fault on line up"
    assert first.list_date == "Sunday Aug 30th 2026"
    assert first.list_date_iso == "2026-08-30"
    assert first.icon == "incident.gif"
    assert first.category == "incident"


def test_date_heading_applies_until_the_next_heading(list_page_html: str):
    records, _ = parse_list_page(list_page_html, source_page="https://avherald.com/")
    assert records[0].list_date == "Sunday Aug 30th 2026"
    assert records[1].list_date == "Saturday Aug 29th 2026"
    assert records[1].list_date_iso == "2026-08-29"
    assert records[1].icon == "accident.gif"
    assert records[1].category == "accident"


def test_next_url_is_absolute(list_page_html: str):
    _, next_url = parse_list_page(list_page_html, source_page="https://avherald.com/")
    assert next_url == (
        "https://avherald.com/h?list=&opt=0&offset=20260821192052%2B53e33032"
    )


def test_nested_tables_do_not_duplicate_rows_or_steal_filter_icons():
    html = """
    <table>
      <tr>
        <td><a href="/h?list=&opt=256"><img src="/images/crash.gif" alt="Crashes On"></a></td>
      </tr>
    </table>
    <table><tr><td><span class="bheadline_avherald">Sunday Aug 30th 2026</span></td></tr></table>
    <table width="100%"><tr bgcolor="#f0f8ff"><td align="left">
      <table width="100%"><tr>
        <td><img class="frame" src="/images/incident.gif" alt="Incident"></td>
        <td>
          <a href="/h?article=53f71a6e&opt=0">
            <span class="headline_avherald">DAT AT42 at Lampedusa on Aug 29th 2026, engine fire indication</span>
          </a>
        </td>
      </tr></table>
    </td></tr></table>
    """
    records, _ = parse_list_page(html, source_page="https://avherald.com/")
    assert len(records) == 1
    row = records[0]
    assert row.article_id == "53f71a6e"
    assert row.category == "incident"
    assert row.icon == "incident.gif"
    assert row.list_date == "Sunday Aug 30th 2026"
    assert row.list_date_iso == "2026-08-30"


def test_page_without_next_returns_none():
    html = """
    <table>
      <tr><td>Monday Aug 24th 2026</td></tr>
      <tr>
        <td><img src="/images/news.gif" alt="News"></td>
        <td>
          <a href="/h?article=53c8958a&opt=0">
            <span class="headline_avherald">AVH was sued</span>
          </a>
        </td>
      </tr>
    </table>
    """
    records, next_url = parse_list_page(html, source_page="https://avherald.com/h?list=")
    assert len(records) == 1
    assert records[0].category == "news"
    assert next_url is None
