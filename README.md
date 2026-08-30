# The Aviation Herald Scraper

Python 3.11+ tool that walks [avherald.com](https://avherald.com/) **list pages** and stores headline metadata in a local SQLite database.

The site has no public API. This scraper only reads what is visible on the listing: article URL, heading, group date, and category icon. **It does not fetch or store article bodies.** There is no AI usage in this project.

## Copyright

> © 2008-2026 by The Aviation Herald, all rights reserved, reproduction, redistribution and AI learning/use prohibited.

Use this as a personal/educational headline archive. Do not redistribute the data, train models on it, or scrape full reports.

`robots.txt` disallows `/` for `User-agent: *`. Keep crawls small, delayed, and headline-only.

## How listing URLs work

Article links look like:

```
https://avherald.com/h?article=53f3f5aa&opt=0
```

`article` is an opaque 8-character hex id (the primary key). `opt` is a list-view flag and is **not** stored. The crawler does **not** enumerate hex ids.

Later pages are reached by following the Next image (`/images/next.jpg`). The `offset` query is `timestamp+last_article_id` on the previous page; it is followed, not constructed.

A listing row is kept only when the link contains `span.headline_avherald` and the table row has a category icon (`incident.gif`, `accident.gif`, `crash.gif`, `news.gif`, `report.gif`). Footer/interview links are ignored.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` if you want to override paths or set `HTTPS_PROXY`.

## Usage

```bash
python -m avherald_scraper
python -m avherald_scraper -n 200 -c incident --sort occurrence
python -m avherald_scraper --dry-run -n 20 -v
python main.py
```

No flags: 50 latest headlines (all categories, sort by update) into `data/avherald.sqlite`. Re-run the same command to fetch the **next** 50; the scraper stores the list-page position and skips `article_id`s already in the database.

Copy `.env.example` to `.env` to keep settings in one place.

From PyCharm, edit the `OPTIONS` list at the top of `main.py` and press Run. Command-line flags passed to `main.py` replace that list.

Optional `avherald.toml` in the project directory (copy `avherald.toml.example`). Precedence: **CLI > env > toml > defaults**.

| Flag | Default | Meaning |
| --- | --- | --- |
| `-n`, `--limit` | `50` | Unique articles to keep |
| `-p`, `--pages` | none | Stop after N list pages |
| `-c`, `--category` | all | `crash`, `accident`, `incident`, `news`, `report` (repeat or CSV) |
| `--sort` | `update` | `update` or `occurrence` |
| `-o`, `--db` | `data/avherald.sqlite` | SQLite file |
| `-d`, `--delay` | `3` | Seconds between list-page requests |
| `--proxy` | env `HTTPS_PROXY` | HTTP(S) proxy |
| `--timeout` | `20` | Request timeout seconds |
| `--dry-run` | off | Parse and print, do not write SQLite |
| `--resume` / `--no-resume` | on | Continue from the last saved list page |
| `--fresh` | off | Ignore the saved position and start from the first list page |
| `--config` | `./avherald.toml` if present | TOML defaults |
| `--start-url` | built from `--sort` / `--category` | Override first list page |
| `-v`, `--verbose` | off | Print each fetched URL and kept rows |
| `-q`, `--quiet` | off | Print nothing on success |

If the site returns the “unauthorized accesses / Botnet” page, the process exits with an error. Pass `--proxy` or set `HTTPS_PROXY`, then retry.

## Database

```sql
SELECT article_id, category, list_date_iso, heading, url FROM articles LIMIT 5;
SELECT COUNT(*) FROM articles;
```

| Column | Content |
| --- | --- |
| `article_id` | 8 hex chars |
| `url` | `https://avherald.com/h?article=<id>` |
| `heading` | Listing headline |
| `list_date` | Date heading printed above the row |
| `list_date_iso` | `YYYY-MM-DD` |
| `icon` | e.g. `incident.gif` |
| `category` | e.g. `incident` |
| `first_seen_at` / `last_seen_at` | UTC ISO-8601 |

`article_id` is the primary key (one row per article). Re-runs skip ids that are already stored and continue from the saved list page in `crawl_state`. Use `--fresh` to start from the first page again (still no duplicate rows).

## Tests

```bash
pytest -v
```

Parser and crawl tests use saved HTML fixtures and never hit the network.
