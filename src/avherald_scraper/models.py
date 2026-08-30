from dataclasses import dataclass


@dataclass(frozen=True)
class ArticleRef:
    """Identity parsed from an article href."""

    article_id: str
    url: str


@dataclass(frozen=True)
class ArticleRecord:
    """One listing-page row: URL plus the metadata shown beside it."""

    article_id: str
    url: str
    heading: str
    list_date: str | None
    list_date_iso: str | None
    icon: str | None
    category: str | None
    source_page: str
