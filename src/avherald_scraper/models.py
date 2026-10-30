"""The two little records the rest of the package passes around.

Nothing in here fetches a page or touches SQLite. These are just the fields.
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

# Frozen dataclasses so a parsed row can't be tweaked later by accident.
from dataclasses import dataclass


# What we keep after reading an article link.
@dataclass(frozen=True)
class ArticleRef:
    """The id and the clean URL taken from one article href."""

    # Eight hex characters. The URL parser has already lowercased them.
    article_id: str

    # Canonical `/h?article=` URL. The list-view `opt` flag is not included.
    url: str


# One visible line on a listing page.
@dataclass(frozen=True)
class ArticleRecord:
    """Headline metadata copied off a single listing row."""

    # Same id as ArticleRef. This becomes the database primary key.
    article_id: str

    # The URL we store. Same canonical shape as ArticleRef.url.
    url: str

    # Text inside `span.headline_avherald`.
    heading: str

    # Date heading printed above the row, still in the site's own wording.
    list_date: str | None

    # That date rewritten as YYYY-MM-DD, when the parser understood it.
    list_date_iso: str | None

    # Icon file name, for example `incident.gif`.
    icon: str | None

    # One of crash, accident, incident, news, report.
    category: str | None

    # The list URL we were on when this row showed up.
    source_page: str
