# AGENTS.md

Instructions for coding agents in this repository.

## Release

The active version is **2.0.0**. It is a complete rewrite of the 1.x script, and it is not tagged yet.

- Keep `[project].version` in `pyproject.toml` and `__version__` in `src/avherald_scraper/__init__.py` identical.
- Put user-visible work in `CHANGELOG.md` under `## [2.0.0] - Unreleased` until `v2.0.0` exists.
- Do not open a 2.1 or 2.2 section. Draft notes that used those numbers describe this rewrite and already belong under 2.0.0.
- Write changelog entries in [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) form. Use headings such as `Features`, `Bug Fixes`, `Breaking Changes`, `Performance Improvements`, `Documentation`, `Code Refactoring`, `Build System`, and `Continuous Integration`. Each bullet is `* scope(action): imperative summary` when a short verb helps (`db(replace)`, `config(load)`), or `* scope: imperative summary` when it does not (`cli`). End every bullet with a Markdown link whose text is the short hash, for example `[#447cdd5](https://github.com/thaikolja/avherald-scraper/commit/447cdd5ae3f3f1f447cc8ec64d783f18395fd6e6)`.

Change runtime code only when the task asks for a behavior change. A documentation task leaves `src/`, `tests/`, and `main.py` alone.

## Product boundaries

This program reads [avherald.com](https://avherald.com/) listing pages and stores headline metadata in SQLite.

- Store `article_id`, canonical URL, heading, list date, icon, and category.
- Leave article report bodies unfetched.
- Follow the Next control (`/images/next.jpg`). Do not guess article ids or `offset` values.
- Send the identifiable `USER_AGENT` in `config.py`. Do not spoof a browser.
- Keep the delay between list-page requests. The default is 3 seconds, and the first request is not delayed.
- Treat the page that contains `has been used for unauthorized accesses` as a block. `http.BlockedError` is the signal, and the CLI exits `1`.
- The site notice prohibits reproduction, redistribution, and AI learning. `robots.txt` disallows `/` for `User-agent: *`. Keep crawls small and headline-only. Do not commit database contents or use them as training data.

The program is MIT licensed. The site text is not.

## Layout

```
pyproject.toml              project metadata, dependencies, console script
src/avherald_scraper/       import package
  cli.py                    argparse and process exit codes
  config.py                 RunConfig and CLI > config.ini > defaults
  urls.py                   article ids, canonical URLs, list-page opt bits
  parser.py                 listing HTML to ArticleRecord; next-page URL
  http.py                   httpx client, delay, block detection
  db.py                     SQLite schema, upsert, crawl_state
  scraper.py                crawl loop
  __main__.py               python -m avherald_scraper
main.py                     IDE launcher only; see Interface
config.ini                  the only settings file; CLI flags win
tests/                      pytest; HTML fixtures; no live network
.gitlab-ci.yml              installs ".[dev]" and runs pytest
```

Generated trees (`*.egg-info/`, `__pycache__/`, `.venv/`, `data/*.sqlite`) stay untracked.

## Interface

The supported command is `avherald-scraper`, from `[project.scripts]`. `python -m avherald_scraper` calls the same `cli.main`.

`main.py` is a local IDE launcher. Its `OPTIONS` list is used only when that file is started with no extra arguments. Do not document it as the interface, and do not remove it unless asked.

Exit codes: `0` success, `1` scrape failure or IP block, `2` invalid configuration.

## Packaging

Declare runtime dependencies in `[project].dependencies` and test tools in `[project.optional-dependencies].dev`. The build backend is setuptools. The package is discovered from `src/`.

Do not add `requirements.txt`, `setup.py`, `Pipfile`, or `setup.cfg`. Do not introduce a lockfile unless the task asks for one.

Python floor is `>=3.11`. Runtime libraries are `beautifulsoup4`, `lxml`, and `httpx`. Settings are read from `config.ini` with the standard-library `configparser`. Do not add `python-dotenv` or a `.env` file.

## Configuration

`load_config` applies sources in this order, highest first: CLI flags, `config.ini`, then `RunConfig` defaults. An unset CLI value must stay `None` in argparse so `config.ini` can fill it. Commented or blank ini keys stay unset. Do not read settings from the environment or from a `.env` file.

| Concern | CLI | config.ini |
| --- | --- | --- |
| Article cap | `-n`, `--limit` | `limit` |
| Page cap | `-p`, `--pages` | `max_pages` |
| Categories | `-c`, `--category` | `categories` |
| Sort | `--sort` | `sort` |
| Database | `-o`, `--db` | `database` |
| Delay | `-d`, `--delay` | `delay` |
| Proxy | `--proxy` | `proxy` |
| Timeout | `--timeout` | `timeout` |
| Resume | `--resume` / `--no-resume` | `resume` |
| Fresh start | `--fresh` | `fresh` |
| Dry run | `--dry-run` | `dry_run` |
| Verbose | `-v`, `--verbose` | `verbose` |
| Origin | | `base_url` |

`--quiet`, `--user-agent`, and `--start-url` are CLI-only. Boolean ini values accept `1`, `true`, `yes`, and `on`.

Categories: `crash`, `accident`, `incident`, `news`, `report`. Empty means all of them. Sort: `update` or `occurrence`.

## Invariants

- An article id matches `^[0-9a-f]{8}$` and is stored lowercase.
- The stored URL is `{origin}/h?article={id}` with no `opt` parameter.
- List-page `opt` bits: `update=0`, `occurrence=1`, `crash=256`, `accident=512`, `incident=1024`, `news=2048`, `report=4096`. `opt=0` is the site root.
- A listing row needs `span.headline_avherald` and one of `crash.gif`, `accident.gif`, `incident.gif`, `news.gif`, `report.gif`. Skip nested `tr` wrappers, footer links, and interview links.
- `articles.article_id` is the primary key. A repeat visit updates heading, dates, icon, category, URL, and `last_seen_at`, and it keeps `first_seen_at`.
- Ids already stored do not count toward `--limit`.
- Resume is on by default. The checkpoint key from `RunConfig.crawl_key` is `{sort}|{categories}` or `url|{start_url}|{categories}`.
- `--fresh` deletes that checkpoint when the run is not a dry run. Dry run does not insert, update, or save a checkpoint. If the database file already exists, a dry run still opens it so known ids can be skipped.
- The default database path is `data/avherald.sqlite`. The parent directory is created on open.

## Tests

Run `pytest` from the repository root after `python3 -m pip install -e ".[dev]"`.

- Parser, HTTP, and crawl tests use `tests/fixtures/` or an injected client.
- Do not add a test that contacts avherald.com.
- HTTP tests pass `httpx.MockTransport`. Crawl tests pass a fake `HtmlFetcher` into `scraper.run`.
- Cover a behavior change in the matching `tests/test_*.py` file.

## Comments

Package modules under `src/avherald_scraper/` and `main.py` carry a casual docstring on every module, class, and function. Each statement has a `#` comment on the line above it and a blank line after the statement. Do not apply that comment style under `tests/`.

## Verification

Run `pytest` before claiming a behavior change is done. Say so only when the command output is in hand. `git diff --check` covers the docs and code you touched.
