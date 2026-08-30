import sys

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

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or OPTIONS))
