from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from avherald_scraper.models import ArticleRef

SITE_ORIGIN = "https://avherald.com"

ARTICLE_ID_RE = re.compile(r"^[0-9a-f]{8}$")
ARTICLE_PATH = "/h"
SORT_OPT = {
    "update": 0,
    "occurrence": 1,
}
CATEGORY_OPT = {
    "crash": 256,
    "accident": 512,
    "incident": 1024,
    "news": 2048,
    "report": 4096,
}
CATEGORIES = tuple(CATEGORY_OPT)


def list_page_url(
    base_url: str,
    *,
    sort: str = "update",
    categories: tuple[str, ...] | list[str] = (),
) -> str:
    """Build a list-page URL from sort order and category filters."""
    if sort not in SORT_OPT:
        raise ValueError(f"sort must be 'update' or 'occurrence', not {sort!r}")
    opt = SORT_OPT[sort]
    for category in categories:
        key = category.lower()
        if key not in CATEGORY_OPT:
            raise ValueError(f"unknown category: {category}")
        opt |= CATEGORY_OPT[key]
    origin = base_url.rstrip("/")
    if opt == 0:
        return f"{origin}/"
    return f"{origin}{ARTICLE_PATH}?list=&opt={opt}"


def canonical_article_url(article_id: str, *, base_url: str = SITE_ORIGIN) -> str:
    article_id = article_id.lower()
    if not ARTICLE_ID_RE.fullmatch(article_id):
        raise ValueError(f"invalid article id: {article_id!r}")
    return f"{base_url.rstrip('/')}{ARTICLE_PATH}?article={article_id}"


def parse_article_href(
    href: str | None,
    *,
    base_url: str = SITE_ORIGIN,
) -> ArticleRef | None:
    """Return an ArticleRef if href is an 8-hex article listing link."""
    if not href:
        return None

    parsed = urlparse(href)
    path = parsed.path or ""
    if path not in (ARTICLE_PATH, f"{ARTICLE_PATH}/"):
        # Relative "/h?article=..." has path "/h". Absolute same.
        if not path.endswith(ARTICLE_PATH):
            return None

    query = parse_qs(parsed.query, keep_blank_values=True)
    values = query.get("article")
    if not values:
        return None
    article_id = values[0].strip().lower()
    if not ARTICLE_ID_RE.fullmatch(article_id):
        return None
    return ArticleRef(article_id=article_id, url=canonical_article_url(article_id, base_url=base_url))
