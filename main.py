"""Editor shortcut for running the scraper with a saved flag list.

The supported command is still `avherald-scraper`. This file is only here so
an IDE Run button has something to point at.
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

# Needed so we can read whatever was typed after `python main.py`.
import sys

# The real program. This file does not scrape anything itself.
from avherald_scraper.cli import main

# Used only when this file is started with no extra CLI arguments.
OPTIONS = [
    "-n", "50",
    "-v",
    # "-c", "incident",
    # "-c", "accident",
    # "--sort", "occurrence",
    # "--dry-run",
    # "--fresh",
    # "--pages", "2",
    # "--proxy", "http://127.0.0.1:8080",
]

# Run when the file is executed, not when it is imported.
if __name__ == "__main__":
    # Extra arguments replace OPTIONS. No arguments means use the list above.
    raise SystemExit(main(sys.argv[1:] or OPTIONS))
