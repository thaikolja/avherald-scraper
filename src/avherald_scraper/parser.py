from __future__ import annotations

import re
from datetime import datetime
from pathlib import PurePosixPath
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from avherald_scraper.config import DEFAULT_BASE_URL
from avherald_scraper.models import ArticleRecord
from avherald_scraper.urls import parse_article_href

BLOCKED_MARKER = "has been used for unauthorized accesses"
CATEGORY_ICONS = {
    "crash.gif": "crash",
    "accident.gif": "accident",
    "incident.gif": "incident",
    "news.gif": "news",
    "report.gif": "report",
}
DATE_HEADING_RE = re.compile(
    r"(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)"
    r"\s+[A-Z][a-z]+\s+\d{1,2}(?:st|nd|rd|th)\s+\d{4}"
)
ORDINAL_SUFFIX_RE = re.compile(r"(?<=\d)(st|nd|rd|th)")


def is_blocked(html: str) -> bool:
    return BLOCKED_MARKER in html


def parse_list_page(
    html: str,
    *,
    source_page: str,
    base_url: str = DEFAULT_BASE_URL,
) -> tuple[list[ArticleRecord], str | None]:
    soup = BeautifulSoup(html, "lxml")
    records: list[ArticleRecord] = []
    current_date: str | None = None

    for row in soup.find_all("tr"):
        if not isinstance(row, Tag):
            continue
        # Listing markup wraps each article in nested tables. Only leaf rows
        # are real date headings or article lines; wrappers re-find the same span.
        if row.find("tr"):
            continue
        heading_date = _date_heading(row)
        if heading_date:
            current_date = heading_date
            continue
        record = _article_from_row(
            row,
            current_date=current_date,
            source_page=source_page,
            base_url=base_url,
        )
        if record:
            records.append(record)

    return records, _next_page_url(soup, base_url=base_url)


def _date_heading(row: Tag) -> str | None:
    if row.find("span", class_="headline_avherald"):
        return None
    bold = row.find("span", class_="bheadline_avherald")
    text = (
        bold.get_text(" ", strip=True)
        if isinstance(bold, Tag)
        else " ".join(row.get_text(" ", strip=True).split())
    )
    match = DATE_HEADING_RE.search(text)
    return match.group(0) if match else None


def _article_from_row(
    row: Tag,
    *,
    current_date: str | None,
    source_page: str,
    base_url: str,
) -> ArticleRecord | None:
    headline = row.find("span", class_="headline_avherald")
    if not isinstance(headline, Tag):
        return None
    link = headline.find_parent("a")
    if not isinstance(link, Tag):
        return None
    ref = parse_article_href(link.get("href"), base_url=base_url)
    if ref is None:
        return None
    icon, category = _category_icon(row)
    if icon is None:
        return None
    heading = headline.get_text(" ", strip=True)
    return ArticleRecord(
        article_id=ref.article_id,
        url=ref.url,
        heading=heading,
        list_date=current_date,
        list_date_iso=_to_iso_date(current_date),
        icon=icon,
        category=category,
        source_page=source_page,
    )


def _category_icon(row: Tag) -> tuple[str | None, str | None]:
    for img in row.find_all("img"):
        if not isinstance(img, Tag):
            continue
        src = img.get("src") or ""
        filename = PurePosixPath(str(src)).name.lower()
        category = CATEGORY_ICONS.get(filename)
        if category:
            return filename, category
    return None, None


def _to_iso_date(date_text: str | None) -> str | None:
    if not date_text:
        return None
    cleaned = ORDINAL_SUFFIX_RE.sub("", date_text)
    try:
        return datetime.strptime(cleaned, "%A %b %d %Y").date().isoformat()
    except ValueError:
        return None


def _next_page_url(soup: BeautifulSoup, *, base_url: str) -> str | None:
    link = soup.select_one('a:has(img[src$="next.jpg"])')
    if not isinstance(link, Tag):
        return None
    href = link.get("href")
    if not href:
        return None
    return urljoin(base_url.rstrip("/") + "/", str(href))
