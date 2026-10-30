# avherald-scraper

Python 3.11+ command that reads [The Aviation Herald](https://avherald.com/) listing pages and stores headline metadata in a local SQLite database.

The site has no public API. Each stored row is the article URL, heading, group date, and category icon shown on the listing.

## Copyright

> © 2008-2026 by The Aviation Herald, all rights reserved, reproduction, redistribution and AI learning/use prohibited.

Use the result as a personal or educational headline archive. Keep crawls small and delayed. The program is [MIT](LICENSE) licensed. The site text is not.

`robots.txt` disallows `/` for `User-agent: *`.

## Installation

Python 3.11 or newer is required. Project metadata and dependencies are declared in `pyproject.toml`.

From a checkout of this repository:

```bash
python3 -m pip install .
avherald-scraper --version
```

Use a virtual environment when the command should stay off the system interpreter:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install .
```

`pipx install .` from the repository root installs the same command in an isolated environment.

## Usage

```bash
avherald-scraper
avherald-scraper --limit 200 --category incident --sort occurrence
avherald-scraper --dry-run --limit 20 --verbose
avherald-scraper --help
```

With no arguments the command stores 50 headlines, in every category, sorted by last update, in `data/avherald.sqlite`.

Run the same command again to take the next 50. The previous list-page position is kept, and an `article_id` that is already stored does not count toward `--limit`. `--fresh` returns to the first list page. Rows remain unique.

`python -m avherald_scraper` invokes the same entry point.

The process exits `0` after a completed run, `1` when a request fails or the site serves its IP-block page, and `2` when the configuration is invalid.

## Configuration

Sources apply in this order: command-line flags, [`config.ini`](config.ini), built-in defaults. A flag you omit does not clear a value set in `config.ini`.

### Command-line flags

| Flag | Default | Meaning |
| --- | --- | --- |
| `-n`, `--limit` | `10` | Unique articles to keep |
| `-p`, `--pages` | none | Stop after this many list pages |
| `-c`, `--category` | all | `crash`, `accident`, `incident`, `news`, `report`; repeat the flag or pass a comma-separated list |
| `--sort` | `update` | `update` or `occurrence` |
| `-o`, `--db` | `data/avherald.sqlite` | SQLite file |
| `-d`, `--delay` | `3` | Seconds between list-page requests |
| `--proxy` | unset | HTTP(S) proxy URL |
| `--timeout` | `20` | Request timeout in seconds |
| `--user-agent` | tool identifier | Value sent in the `User-Agent` header |
| `--dry-run` | off | Parse and print rows, and leave the database unchanged |
| `--resume` / `--no-resume` | on | Continue from the saved list page |
| `--fresh` | off | Drop the saved position and start at the first list page |
| `--config` | `config.ini` in the project root | INI settings file |
| `--start-url` | built from sort and category | First list page |
| `-v`, `--verbose` | off | Print each fetched URL and the kept rows |
| `-q`, `--quiet` | off | Print nothing after a successful run |

### config.ini

[`config.ini`](config.ini) sits in the project root and holds the default crawl. Edit it in place. A command-line flag for the same setting overrides the file. Boolean values are `true` or `false`. Commented keys are left unset.

| Key | Section | Flag |
| --- | --- | --- |
| `base_url` | `site` | |
| `database` | `storage` | `-o`, `--db` |
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

Pass `--config path/to/config.ini` to use a different file for that run.

If the response contains the site's unauthorized-access page, set `proxy` in `config.ini` or pass `--proxy`, then run the command again.

## Listing pages

Article links look like `https://avherald.com/h?article=53f3f5aa&opt=0`.

`article` is an opaque 8-character hexadecimal id and the primary key. `opt` selects the list view and is omitted from the stored URL. Later pages come from the Next image, `/images/next.jpg`. The crawler follows that link.

A row is stored when the link contains `span.headline_avherald` and the table row carries a category icon: `incident.gif`, `accident.gif`, `crash.gif`, `news.gif`, or `report.gif`. Footer and interview links are ignored.

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

A later crawl refreshes the heading, dates, icon, and category, and it leaves `first_seen_at` in place. `crawl_state` holds the resume URL for each sort and category selection.

## Development

```bash
python3 -m pip install -e ".[dev]"
pytest
```

The `dev` extra installs pytest. Tests under `tests/` read saved HTML fixtures and do not contact the network. GitLab CI runs the same install and `pytest tests/` on Python 3.13.

See [AGENTS.md](AGENTS.md) for repository conventions.
