"""Read a listing page into headline rows, plus the link to the next page.

Footer links and interview blurbs are ignored. A row counts when it has the
headline span and one of the category icons.
"""

#  @name:           The Aviation Herald (avherald)
#  @description     Unofficial CLI tool to scrape data from avherald.com and store it in a .sqlite database.
#  @author          Kolja Nolte <kolja.nolte@gmail.com>
#  @copyright       2025-2026 (C) Kolja Nolte
#  @see             https://docs.kolja-nolte.com/av-herald
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  Released under the GNU General Public License v2 or later.
#  See: https://www.gnu.org/licenses/gpl-2.0.html
#
#  @package AVH
#  @license GPL-2.0-or-later

# Annotations in this file refer to types defined below the imports.
from __future__ import annotations

# Two patterns: the date heading, and the "1st/2nd/3rd" suffixes on it.
import re

# Listing dates are parsed with the standard library, not a third-party lib.
from datetime import datetime

# Icon names are the last piece of an image path, even when that path is a URL.
from pathlib import PurePosixPath

# Next-page hrefs are often relative. They need the site origin glued on.
from urllib.parse import urljoin

# lxml is the parser BeautifulSoup is asked to use.
from bs4 import BeautifulSoup, Tag

# Default origin, so callers can omit it when they mean the public site.
from avherald_scraper.config import DEFAULT_BASE_URL

# The row we hand back once a line has passed the filters.
from avherald_scraper.models import ArticleRecord

# Turns an href into an id, or None when the link is not an article.
from avherald_scraper.urls import parse_article_href

# A sentence that only shows up on the IP-block page.
BLOCKED_MARKER = "has been used for unauthorized accesses"

# Map the icon file to the category name stored in SQLite.
CATEGORY_ICONS = {
    "crash.gif": "crash",
    "accident.gif": "accident",
    "incident.gif": "incident",
    "news.gif": "news",
    "report.gif": "report",
}

# Matches headings like "Monday Jan 2nd 2024".
DATE_HEADING_RE = re.compile(
    r"(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)"
    r"\s+[A-Z][a-z]+\s+\d{1,2}(?:st|nd|rd|th)\s+\d{4}"
)

# Strips those ordinal suffixes so strptime can read the day number.
ORDINAL_SUFFIX_RE = re.compile(r"(?<=\d)(st|nd|rd|th)")


def is_blocked(html: str) -> bool:
    """True when this HTML is the site's unauthorized-access page."""

    # A substring check is enough. The sentence is very specific.
    return BLOCKED_MARKER in html


def parse_list_page(
    html: str,
    *,
    source_page: str,
    base_url: str = DEFAULT_BASE_URL,
) -> tuple[list[ArticleRecord], str | None]:
    """Pull headline rows and the next-page URL out of one listing."""

    # lxml handles the site's old nested tables better than the builtin parser.
    soup = BeautifulSoup(html, "lxml")

    # Rows are appended in the order they appear on the page.
    records: list[ArticleRecord] = []

    # Date headings apply to every article row until the next heading.
    current_date: str | None = None

    # The listing is a pile of tables. Walk every row.
    for row in soup.find_all("tr"):
        # BeautifulSoup can hand back a navigable string-ish node. Skip those.
        if not isinstance(row, Tag):
            # Only real tags have the child elements we look for.
            continue

        # Nested tables repeat the same headline. Only the leaf row is real.
        if row.find("tr"):
            # This one is a wrapper, so the inner row will be seen on its own.
            continue

        # A bold date line updates the date used by the following articles.
        heading_date = _date_heading(row)

        # Headings are not articles, and they replace the date seen so far.
        if heading_date:
            # Later rows keep this date until another heading shows up.
            current_date = heading_date

            # Don't also try to read this row as an article.
            continue

        # Try to turn the row into one stored headline.
        record = _article_from_row(
            row,
            current_date=current_date,
            source_page=source_page,
            base_url=base_url,
        )

        # None means the row was a footer, an interview, or a half-empty line.
        if record:
            # Keep the page order.
            records.append(record)

    # The next URL is None on the last page.
    return records, _next_page_url(soup, base_url=base_url)


def _date_heading(row: Tag) -> str | None:
    """Return the date text when this row is a date heading, else None."""

    # Article rows also contain bold text. The headline span marks them apart.
    if row.find("span", class_="headline_avherald"):
        # This is an article line, not a date.
        return None

    # Date lines use a different class from article headlines.
    bold = row.find("span", class_="bheadline_avherald")

    # Prefer that span. Fall back to the row's own text if it isn't there.
    text = (
        bold.get_text(" ", strip=True)
        if isinstance(bold, Tag)
        else " ".join(row.get_text(" ", strip=True).split())
    )

    # The heading has a weekday, a month, an ordinal day, and a year.
    match = DATE_HEADING_RE.search(text)

    # Hand back the matched wording, or nothing if this row isn't a date.
    return match.group(0) if match else None


def _article_from_row(
    row: Tag,
    *,
    current_date: str | None,
    source_page: str,
    base_url: str,
) -> ArticleRecord | None:
    """Build one record from a leaf row, or None when the row doesn't qualify."""

    # The headline span is the easiest way to spot a real article line.
    headline = row.find("span", class_="headline_avherald")

    # Date headings and spacer rows don't have it.
    if not isinstance(headline, Tag):
        # Not an article.
        return None

    # The span sits inside the link that points at the article.
    link = headline.find_parent("a")

    # No link means there is no href to store.
    if not isinstance(link, Tag):
        # Skip it.
        return None

    # Pull the id out of the href. opt= is dropped in there.
    ref = parse_article_href(link.get("href"), base_url=base_url)

    # Interviews and other /h links that aren't eight hex ids come back None.
    if ref is None:
        # Leave them out.
        return None

    # The category comes from the gif on the same row.
    icon, category = _category_icon(row)

    # Rows without a known category icon are not part of the listing.
    if icon is None:
        # Filters and decoration use other images. Ignore those.
        return None

    # Collapse whitespace so the stored heading is one clean line.
    heading = headline.get_text(" ", strip=True)

    # Dates that don't parse still keep the original wording in list_date.
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
    """Return `(filename, category)` for the first known icon on the row."""

    # A row can contain extra images. The first known gif wins.
    for img in row.find_all("img"):
        # Same guard as the row walk. Only real tags have a src.
        if not isinstance(img, Tag):
            # Keep looking.
            continue

        # Missing src is treated as an empty path.
        src = img.get("src") or ""

        # The category table is keyed by the file name, not the whole path.
        filename = PurePosixPath(str(src)).name.lower()

        # Unknown images, including the Next button, are not categories.
        category = CATEGORY_ICONS.get(filename)

        # Stop at the first match so a later decoration can't override it.
        if category:
            # The caller stores both the file name and the short category.
            return filename, category

    # No crash/accident/incident/news/report icon on this row.
    return None, None


def _to_iso_date(date_text: str | None) -> str | None:
    """Turn a listing date heading into `YYYY-MM-DD`, or None."""

    # Rows above the first date heading have nothing to convert.
    if not date_text:
        # Leave the ISO column empty.
        return None

    # "2nd" has to become "2" before strptime will accept it.
    cleaned = ORDINAL_SUFFIX_RE.sub("", date_text)

    # The heading looks like "Monday Jan 2 2024" once the suffix is gone.
    try:
        # date() drops the time. isoformat() is YYYY-MM-DD.
        return datetime.strptime(cleaned, "%A %b %d %Y").date().isoformat()

    # A heading that looked date-like but doesn't match the pattern.
    except ValueError:
        # Keep list_date, and store no ISO value.
        return None


def _next_page_url(soup: BeautifulSoup, *, base_url: str) -> str | None:
    """Return the absolute URL behind the Next image, or None on the last page."""

    # The site uses an image named next.jpg inside the link, not a text label.
    link = soup.select_one('a:has(img[src$="next.jpg"])')

    # Last page, or markup we don't recognise.
    if not isinstance(link, Tag):
        # The crawl stops when this comes back empty.
        return None

    # The image is found. The href is what we actually follow.
    href = link.get("href")

    # A next image with no href isn't a page we can request.
    if not href:
        # Treat that like the end of the list.
        return None

    # Relative hrefs need the origin. A trailing slash keeps urljoin honest.
    return urljoin(base_url.rstrip("/") + "/", str(href))
