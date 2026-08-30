# Changelog

## v2.2.0

- **No duplicates:** `article_id` is unique. Already-stored ids are skipped and do not count toward `--limit`.
- **Resume:** each run saves the list-page position in `crawl_state`. The next run continues from there instead of restarting at the homepage. `--fresh` (or `AVHERALD_FRESH=true`) starts over.
- **`.env.example`:** documents every setting (`AVHERALD_LIMIT`, sort, categories, resume, proxy, …).

## v2.1.0

Easier default run, more knobs when you need them.

- **Defaults:** `avherald-scraper` with no flags still stores 50 headlines. Short flags: `-n`, `-c`, `-o`, `-d`, `-p`, `-v`, `-q`.
- **PyCharm:** edit the `OPTIONS` list in `main.py` and press Run.
- **Config file:** optional `avherald.toml` (see `avherald.toml.example`). CLI > env > toml > defaults.
- **Filters:** `--category incident` (repeatable or CSV), `--sort update|occurrence` (maps to the site `opt=` bitfield).
- **Caps:** `--pages N` in addition to `--limit`. `--dry-run` prints rows without writing SQLite.
- **Network:** `--proxy`, `--timeout`, `--user-agent`.

## v2.0.0

Rebuild as a small package that crawls list pages, not article bodies.

- **URL grammar:** Article links match `/h?article=<8-hex>` and are stored without `opt=`. Pagination follows the Next control; IDs are not guessed.
- **Records:** Each row is `article_id`, canonical URL, heading, list date, icon/category.
- **SQLite:** Upsert on `article_id` in `data/avherald.sqlite`. Re-crawls update heading/date/icon and keep `first_seen_at`.
- **Layout:** `src/avherald_scraper/` modules for URLs, HTTP, parser, database, scrape loop, and CLI.
- **Politeness:** Delay between list-page requests, identifiable User-Agent, IP-block detection, optional `HTTPS_PROXY`.
- **CLI:** `python -m avherald_scraper --limit 50`

## v1.0.2

This release introduces configurable settings via environment variables and includes infrastructure improvements.

Key updates:

- **Configuration:** Application settings (like base URL and database path) are now managed using environment variables loaded from a `.env` file.
- **Proxy Support:** Changed the request URL handling, likely to support proxying requests (as noted in the changelog).
- **Dependency Management:** Added linting tools (flake8) and updated dependencies in `requirements.txt`.
- **Build Process:** Updated GitLab CI configuration to ensure all dependencies are installed.
- **Project Structure:** Added `CHANGELOG.md` and refined `.gitignore` and output directory handling.

## v1.0.1

* Changed the location of the output to `/output/data.sqlite`
