# Changelog

All notable changes to this project are documented in this file.

The format follows [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - Unreleased

Complete rewrite of the 1.x script as a `src/` package. Listing headlines are stored by article id.

### Breaking Changes

* cli: provide `avherald-scraper` as the supported command [#447cdd5](https://github.com/thaikolja/avherald-scraper/commit/447cdd5ae3f3f1f447cc8ec64d783f18395fd6e6)
* packaging: declare dependencies in `pyproject.toml` and install with pip [#447cdd5](https://github.com/thaikolja/avherald-scraper/commit/447cdd5ae3f3f1f447cc8ec64d783f18395fd6e6)
* db(replace): replace the `incidents` table with `articles`, keyed by `article_id` [#447cdd5](https://github.com/thaikolja/avherald-scraper/commit/447cdd5ae3f3f1f447cc8ec64d783f18395fd6e6)
* db: write the default database to `data/avherald.sqlite` [#447cdd5](https://github.com/thaikolja/avherald-scraper/commit/447cdd5ae3f3f1f447cc8ec64d783f18395fd6e6)
* records: store the canonical article URL, heading, list date, and category icon [#447cdd5](https://github.com/thaikolja/avherald-scraper/commit/447cdd5ae3f3f1f447cc8ec64d783f18395fd6e6)
* filter: keep every category unless one is requested, including `news` [#447cdd5](https://github.com/thaikolja/avherald-scraper/commit/447cdd5ae3f3f1f447cc8ec64d783f18395fd6e6)
* http: send a tool User-Agent on listing requests [#447cdd5](https://github.com/thaikolja/avherald-scraper/commit/447cdd5ae3f3f1f447cc8ec64d783f18395fd6e6)

### Features

* urls: accept `/h?article=<8-hex>` links and drop the list-view `opt` parameter [#447cdd5](https://github.com/thaikolja/avherald-scraper/commit/447cdd5ae3f3f1f447cc8ec64d783f18395fd6e6)
* urls(build): build the first list URL from `--sort` and `--category` [#447cdd5](https://github.com/thaikolja/avherald-scraper/commit/447cdd5ae3f3f1f447cc8ec64d783f18395fd6e6)
* parser: follow the Next control and ignore footer and interview links [#447cdd5](https://github.com/thaikolja/avherald-scraper/commit/447cdd5ae3f3f1f447cc8ec64d783f18395fd6e6)
* db(upsert): upsert on `article_id` and preserve `first_seen_at` [#447cdd5](https://github.com/thaikolja/avherald-scraper/commit/447cdd5ae3f3f1f447cc8ec64d783f18395fd6e6)
* db(save): save the list-page position in `crawl_state` [#447cdd5](https://github.com/thaikolja/avherald-scraper/commit/447cdd5ae3f3f1f447cc8ec64d783f18395fd6e6)
* scraper(skip): skip stored ids so they do not count toward `--limit` [#447cdd5](https://github.com/thaikolja/avherald-scraper/commit/447cdd5ae3f3f1f447cc8ec64d783f18395fd6e6)
* cli(resume): resume from the saved list page, and add `--fresh` to start again [#447cdd5](https://github.com/thaikolja/avherald-scraper/commit/447cdd5ae3f3f1f447cc8ec64d783f18395fd6e6)
* cli: add `--limit`, `--pages`, `--category`, `--sort`, `--db`, and `--delay` [#447cdd5](https://github.com/thaikolja/avherald-scraper/commit/447cdd5ae3f3f1f447cc8ec64d783f18395fd6e6)
* cli: add `--dry-run`, `--proxy`, `--timeout`, `--user-agent`, `--verbose`, and `--quiet` [#447cdd5](https://github.com/thaikolja/avherald-scraper/commit/447cdd5ae3f3f1f447cc8ec64d783f18395fd6e6)
* config(load): load `avherald.toml` and `.env`, with CLI overriding environment, file, and defaults [#447cdd5](https://github.com/thaikolja/avherald-scraper/commit/447cdd5ae3f3f1f447cc8ec64d783f18395fd6e6)
* config(ini): read default settings from `config.ini` in the project root, and let CLI flags override that file
* config(remove): drop `.env` and environment variables; settings live only in `config.ini`
* http(delay): wait between list-page requests and stop when the IP-block page is returned [#447cdd5](https://github.com/thaikolja/avherald-scraper/commit/447cdd5ae3f3f1f447cc8ec64d783f18395fd6e6)

### Continuous Integration

* ci: install the project with `pip install -e ".[dev]"` before `pytest` [#447cdd5](https://github.com/thaikolja/avherald-scraper/commit/447cdd5ae3f3f1f447cc8ec64d783f18395fd6e6)

## [1.0.2] - 2025-05-12

### Features

* config(load): load `BASE_URL` and `DATABASE_FILE_PATH` from a `.env` file [#3286e11](https://github.com/thaikolja/avherald-scraper/commit/3286e1144237abce882d165ba3e82f4b8e8b81cb)

### Build System

* build(deps): track install dependencies in `requirements.txt` [#3286e11](https://github.com/thaikolja/avherald-scraper/commit/3286e1144237abce882d165ba3e82f4b8e8b81cb)
* lint: add flake8 [#3286e11](https://github.com/thaikolja/avherald-scraper/commit/3286e1144237abce882d165ba3e82f4b8e8b81cb)

### Continuous Integration

* ci: install dependencies before the test job [#ab113cb](https://github.com/thaikolja/avherald-scraper/commit/ab113cb1244c15e526fb2ba212696044c67c6423)

### Miscellaneous Chores

* repo: add `CHANGELOG.md` [#7a5be91](https://github.com/thaikolja/avherald-scraper/commit/7a5be91c225cb0e9b47c4fe4883d6df892b2fa6d)
* repo: keep `output/` in the tree and ignore generated files there [#fac12df](https://github.com/thaikolja/avherald-scraper/commit/fac12df2c8ffb71893a5e2c13f994fd2b074b40a)

## [1.0.1] - 2025-05-11

### Features

* scraper(skip): skip listings in the `news` category [#6edbea6](https://github.com/thaikolja/avherald-scraper/commit/6edbea63629ec097a4c2bb71fb245151ae47ec41)

[2.0.0]: https://github.com/thaikolja/avherald-scraper/compare/v1.0.2...HEAD
[1.0.2]: https://github.com/thaikolja/avherald-scraper/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/thaikolja/avherald-scraper/compare/v1.0.0...v1.0.1
