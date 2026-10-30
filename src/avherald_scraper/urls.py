"""Turn Aviation Herald links into ids and list-page URLs.

Article ids are never guessed. A link counts only when it already carries an
8-character hex id, and the next page is somebody else's problem: the parser
follows the Next control instead of building an offset.
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

# Let annotations mention names that show up later in the file.
from __future__ import annotations

# Used to check that an article id is eight hex characters.
import re

# Listing links arrive as relative paths or full URLs.
from urllib.parse import parse_qs, urlparse

# The small id-and-url pair handed back to the parser.
from avherald_scraper.models import ArticleRef

# Canonical URLs are built against the public site.
SITE_ORIGIN = "https://avherald.com"

# An article id is exactly eight lowercase hex characters.
ARTICLE_ID_RE = re.compile(r"^[0-9a-f]{8}$")

# Article pages and filtered listings both live under this path.
ARTICLE_PATH = "/h"

# The site stores the sort order in the low bits of `opt`.
SORT_OPT = {
    "update": 0,
    "occurrence": 1,
}

# Category filters sit in the higher bits and can be combined with the sort.
CATEGORY_OPT = {
    "crash": 256,
    "accident": 512,
    "incident": 1024,
    "news": 2048,
    "report": 4096,
}

# Stable name order for errors and the `--category` help text.
CATEGORIES = tuple(CATEGORY_OPT)


# First page for this sort order and these category filters.
def list_page_url(
    base_url: str,
    *,
    sort: str = "update",
    categories: tuple[str, ...] | list[str] = (),
) -> str:
    """Build a list-page URL from a sort order and category filters."""

    # The site only sorts two ways.
    if sort not in SORT_OPT:
        # Name the bad value instead of building a nonsense URL.
        raise ValueError(f"sort must be 'update' or 'occurrence', not {sort!r}")

    # Start from the sort bit. `update` is zero, which keeps the homepage bare.
    opt = SORT_OPT[sort]

    # Mix every requested category into that same bitfield.
    for category in categories:
        # Callers sometimes pass mixed case. The bit table is lowercase.
        key = category.lower()

        # A typo should fail loudly, not quietly crawl everything.
        if key not in CATEGORY_OPT:
            # Repeat the unknown name so it is easy to spot.
            raise ValueError(f"unknown category: {category}")

        # Several categories can be on at the same time.
        opt |= CATEGORY_OPT[key]

    # Avoid a double slash if the caller already included one.
    origin = base_url.rstrip("/")

    # Zero means "latest updates", which is just the site root.
    if opt == 0:
        # No query string on that URL.
        return f"{origin}/"

    # `list=` is the site's own marker for a filtered front page.
    return f"{origin}{ARTICLE_PATH}?list=&opt={opt}"


# The URL we store, with the list-view opt flag left off.
def canonical_article_url(article_id: str, *, base_url: str = SITE_ORIGIN) -> str:
    """Build the stored article URL, without the list-view `opt` flag."""

    # One case only, so the same id can't be stored twice.
    article_id = article_id.lower()

    # Reject anything that is not eight hex characters.
    if not ARTICLE_ID_RE.fullmatch(article_id):
        # Do not invent a URL for a bad id.
        raise ValueError(f"invalid article id: {article_id!r}")

    # This is the form that goes into the database.
    return f"{base_url.rstrip('/')}{ARTICLE_PATH}?article={article_id}"


# Pull an article id out of a href, or give up when it isn't one.
def parse_article_href(
    href: str | None,
    *,
    base_url: str = SITE_ORIGIN,
) -> ArticleRef | None:
    """Return an ArticleRef when href is an 8-hex article listing link."""

    # Spacer tags and broken markup show up with no href at all.
    if not href:
        # That is not an article.
        return None

    # Split the path from the query so each can be checked on its own.
    parsed = urlparse(href)

    # A relative link still has a path. A missing one is an empty string.
    path = parsed.path or ""

    # `/h` is the usual article path. Anything else must still end in `/h`.
    if (
        path not in (ARTICLE_PATH, f"{ARTICLE_PATH}/")
        and not path.endswith(ARTICLE_PATH)
    ):
        # Login links, footer links, and the list page itself stop here.
        return None

    # Keep blank values so an empty `article=` is different from a missing one.
    query = parse_qs(parsed.query, keep_blank_values=True)

    # `opt` is a list-view flag and is ignored on purpose.
    values = query.get("article")

    # A `/h` link with no article id is a listing, not a story.
    if not values:
        # Nothing to store.
        return None

    # Take the first value, trim it, and fold the case.
    article_id = values[0].strip().lower()

    # Skip ids that are the wrong length or not hex.
    if not ARTICLE_ID_RE.fullmatch(article_id):
        # A bad key is worse than a skipped row.
        return None

    # The parser gets the id and the clean URL together.
    return ArticleRef(
        article_id=article_id,
        url=canonical_article_url(article_id, base_url=base_url),
    )
