# avherald-scraper

Python 3.11+ command that reads [The Aviation Herald](https://avherald.com/) listing pages and stores headline metadata in a local SQLite database.

The site has no public API. A stored row is the article URL, heading, group date, and category icon from the listing. Article report bodies are not requested.

> [!WARNING]
> This project is not affiliated with The Aviation Herald. The [Impressum](https://avherald.com/h?impressum=) identifies the publisher as NOMIS SOFT in Salzburg. The notice on that page, and on the rest of the site, says: "© 2008-2026 by The Aviation Herald, all rights reserved, reproduction, redistribution and AI learning/use prohibited." `robots.txt` disallows `/`.
>
> The program is original code. It does not ship the site's text. A small local copy of listing headlines can still be argued as fair use under [17 U.S.C. § 107](https://www.law.cornell.edu/uscode/text/17/107): the material is short and factual, the purpose is a personal or educational reference rather than a substitute for the articles, the amount is limited to headline metadata, and the copy is not republished or used to train a model. Fair use is a case-by-case defense, not permission from the publisher. It does not cover bulk republication or AI training. The publisher is Austrian, so US fair use is not the site's own rule. Keep crawls small and delayed.

The program is [MIT](LICENSE) licensed. The site's text is not.

## Installation

Python 3.11 or newer. Dependencies are declared in `pyproject.toml`.

```bash
python3 -m pip install .
avherald-scraper --version
```

Isolate the install when it should stay off the system interpreter:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install .
```

`pipx install .` from the repository root installs the command in its own environment.

## Usage

```bash
avherald-scraper
avherald-scraper --limit 3 --format cli
avherald-scraper --limit 200 --category incident --sort occurrence
avherald-scraper --dry-run --limit 20 --verbose
avherald-scraper --help
```

With no arguments the command uses [`config.ini`](config.ini): currently 10 headlines, every category, sorted by last update, stored in `data/avherald.sqlite`.

Run the same command again for the next batch. The saved list-page position is kept, and an `article_id` already stored does not count toward `--limit`. `--fresh` returns to the first list page. Rows stay unique.

`python -m avherald_scraper` is the same entry point.

Exit status: `0` finished, `1` request failure or IP-block page, `2` invalid configuration.

On a terminal, a progress bar stays on stderr while pages are fetched. `--quiet` hides it. The summary on stdout lists only the counts that changed.

## Configuration

Command-line flags win, then [`config.ini`](config.ini), then built-in defaults. Omitting a flag does not clear the value in `config.ini`.

### Flags

| Flag | Default | Meaning |
| --- | --- | --- |
| `-n`, `--limit` | `10` | Unique articles to keep |
| `-p`, `--pages` | none | Stop after this many list pages |
| `-c`, `--category` | all | `crash`, `accident`, `incident`, `news`, `report`. Repeat the flag or use commas |
| `--sort` | `update` | `update` or `occurrence` |
| `-o`, `--db` | `data/avherald.sqlite` | SQLite store. Resume always uses this file |
| `--format` | `sqlite` | `sqlite`, `json`, `csv`, `xlsx`, or `cli` |
| `-d`, `--delay` | `3` | Seconds between list-page requests |
| `--proxy` | direct | HTTP(S) proxy. Repeat the flag or use commas. A ban tries the next host |
| `--timeout` | `20` | Request timeout in seconds |
| `--user-agent` | tool identifier | `User-Agent` header |
| `--dry-run` | off | Parse and print. Do not write |
| `--resume` / `--no-resume` | on | Continue from the saved list page |
| `--fresh` | off | Drop the saved position and start at the first list page |
| `--config` | `config.ini` in the project root | Settings file for this run |
| `--start-url` | built from sort and category | First list page |
| `--show-config` | | Print the effective settings and exit |
| `-v`, `--verbose` | off | List the kept headlines |
| `-q`, `--quiet` | off | No progress bar and no summary |

### config.ini

Edit [`config.ini`](config.ini) in the project root. Booleans are `true` or `false`. Commented keys stay unset. `--config path/to/config.ini` selects another file.

| Key | Section | Flag |
| --- | --- | --- |
| `base_url` | `site` | |
| `database` | `storage` | `-o`, `--db` |
| `format` | `storage` | `--format` |
| `limit` | `crawl` | `-n`, `--limit` |
| `sort` | `crawl` | `--sort` |
| `categories` | `crawl` | `-c`, `--category` |
| `max_pages` | `crawl` | `-p`, `--pages` |
| `resume` | `crawl` | `--resume` |
| `fresh` | `crawl` | `--fresh` |
| `dry_run` | `crawl` | `--dry-run` |
| `verbose` | `crawl` | `-v`, `--verbose` |
| `delay` | `network` | `-d`, `--delay` |
| `timeout` | `network` | `--timeout` |
| `proxy` | `network` | `--proxy` |

If the site returns its unauthorized-access page, set `proxy` or pass `--proxy` and run again.

## Output

`sqlite` writes `data/avherald.sqlite` and nothing else.

`json`, `csv`, and `xlsx` are copies beside that file (`data/avherald.json`, and the same stem for the other two). Resume still uses the SQLite file.

`cli` prints a few headlines in the terminal, with space between the category, date, heading, and URL. It is meant for a small limit. No extra file is written.

Apple Pages (`.pages`) is a private package format. This program does not write it. Open the `.xlsx` or `.csv` in Pages.

## Listing pages

Article links look like `https://avherald.com/h?article=53f3f5aa&opt=0`.

`article` is an opaque 8-character hexadecimal id and the primary key. `opt` selects the list view and is omitted from the stored URL. The next page is the link around `/images/next.jpg`. The crawler follows that link and does not guess offsets.

A row is stored when the link contains `span.headline_avherald` and the row carries `incident.gif`, `accident.gif`, `crash.gif`, `news.gif`, or `report.gif`. Footer and interview links are ignored.

The first list URL is the site root when sort is `update` and no category is selected. Other combinations set the site's `opt` bitfield: occurrence `1`, crash `256`, accident `512`, incident `1024`, news `2048`, report `4096`.

## Database

```sql
SELECT article_id, category, list_date_iso, heading, url
FROM articles
LIMIT 5;
```

| Column | Content |
| --- | --- |
| `article_id` | 8 hexadecimal characters, primary key |
| `url` | `https://avherald.com/h?article=<id>` |
| `heading` | Listing headline |
| `list_date` | Date heading printed above the row |
| `list_date_iso` | `YYYY-MM-DD` |
| `icon` | File name, for example `incident.gif` |
| `category` | `crash`, `accident`, `incident`, `news`, or `report` |
| `source_page` | List URL that contained the row |
| `first_seen_at`, `last_seen_at` | UTC timestamps |

A later crawl refreshes the heading, dates, icon, and category, and leaves `first_seen_at` in place. `crawl_state` holds the resume URL for each sort and category selection.

## Development

```bash
python3 -m pip install -e ".[dev]"
pytest
```

Tests read saved HTML fixtures and do not contact the network. GitLab CI runs that install and `pytest tests/` on Python 3.13.

See [CONTRIBUTING.md](CONTRIBUTING.md).
