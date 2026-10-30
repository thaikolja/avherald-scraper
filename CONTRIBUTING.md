# Contributing

Bugs, tests, and small patches are welcome. Open an issue or a merge request against the `v2` branch.

## Boundaries

- Store listing headlines only. Do not fetch or store article report bodies.
- Do not add a path that redistributes scraped text or feeds it to a model.
- Keep the delay between list-page requests. Do not add parallel fetches.
- Follow the Next control. Do not guess article ids or page offsets.
- The site notice prohibits reproduction, redistribution, and AI use. See the warning in [README.md](README.md).

## Setup

Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
pytest
```

Dependencies belong in `pyproject.toml`. Do not add `requirements.txt`, `setup.py`, or a `.env` file. Settings live in `config.ini`. Command-line flags override that file.

## Tests

Tests live in `tests/` and use HTML fixtures. A test must not contact avherald.com. Inject `httpx.MockTransport` or a fake client.

`ruff check` should pass on the files you touch.

## What not to commit

- `data/*.sqlite` and other database files
- `.venv/`
- `AGENTS.md` (local notes only; it is gitignored)
- Secrets, proxy credentials, or a filled-in private `config.ini` if you put credentials in it

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

```text
feat(cli): describe the user-visible change
fix(parser): describe the bug
```

User-visible changes also get a line in `CHANGELOG.md` under `## [2.0.0] - Unreleased`.
