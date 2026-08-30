from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from dotenv import load_dotenv

from avherald_scraper.urls import CATEGORIES, SITE_ORIGIN, list_page_url

load_dotenv()

DEFAULT_BASE_URL = SITE_ORIGIN
DEFAULT_DATABASE_PATH = Path("data/avherald.sqlite")
DEFAULT_REQUEST_DELAY_SECONDS = 3.0
DEFAULT_LIMIT = 50
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_CONFIG_NAME = "avherald.toml"

USER_AGENT = (
    "avherald-scraper/2.0 (+https://github.com/thaikolja/avherald-scraper; "
    "headlines-only personal archive)"
)


@dataclass(frozen=True)
class RunConfig:
    """
    Configuration object for running a data collection or web crawling process.

    This class represents various configuration options for managing a web crawling or
    data collection process, such as throttling requests, handling proxy settings,
    defining the target categories for crawling, and managing output behavior.
    It is built as an immutable dataclass to ensure the configuration remains
    unchanged once created. This immutability enhances safety in concurrent or
    multi-threaded environments.

    :ivar limit: Maximum number of items to process during the run.
    :type limit: int
    :ivar delay: Delay (in seconds) between consecutive requests to the server.
    :type delay: float
    :ivar database_path: Path to the database file for storing results.
    :type database_path: Path
    :ivar base_url: The base URL to be used as a starting point for web crawling.
    :type base_url: str
    :ivar start_url: (Optional) A specific URL to start the crawling process. Defaults to None.
    :type start_url: str | None
    :ivar sort: Sort order for the crawling process. Default is "update".
    :type sort: str
    :ivar categories: Categories to filter items being crawled.
    :type categories: tuple[str, ...]
    :ivar max_pages: (Optional) Maximum number of pages to traverse. Defaults to None.
    :type max_pages: int | None
    :ivar proxy: (Optional) Proxy URL for the crawling requests. Defaults to None.
    :type proxy: str | None
    :ivar timeout: Timeout (in seconds) for a single request. Defaults to ``DEFAULT_TIMEOUT_SECONDS``.
    :type timeout: float
    :ivar user_agent: User agent string to be used in requests.
    :type user_agent: str
    :ivar dry_run: If True, execute without making changes or saving results. Default is False.
    :type dry_run: bool
    :ivar verbose: If True, enable verbose output during the process. Default is False.
    :type verbose: bool
    :ivar quiet: If True, suppress all output except critical errors. Default is False.
    :type quiet: bool
    :ivar resume: If True, resume a previously interrupted crawl. Default is True.
    :type resume: bool
    :ivar fresh: If True, start a fresh crawl and discard previous states. Default is False.
    :type fresh: bool
    """
    __dataclass_fields__ = None
    limit: int = DEFAULT_LIMIT
    delay: float = DEFAULT_REQUEST_DELAY_SECONDS
    database_path: Path = DEFAULT_DATABASE_PATH
    base_url: str = DEFAULT_BASE_URL
    start_url: str | None = None
    sort: str = "update"
    categories: tuple[str, ...] = ()
    max_pages: int | None = None
    proxy: str | None = None
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    user_agent: str = USER_AGENT
    dry_run: bool = False
    verbose: bool = False
    quiet: bool = False
    resume: bool = True
    fresh: bool = False

    def resolved_start_url(self) -> str:
        """
        Resolves and returns the start URL based on the attributes of the instance.

        This method checks if a `start_url` is explicitly provided. If so, it returns
        the `start_url`. Otherwise, it generates a URL using the `list_page_url`
        helper and returns the constructed URL.

        :return: Resolved start URL as a string
        :rtype: str
        """

        if self.start_url:
            return self.start_url
        return list_page_url(self.base_url, sort=self.sort, categories=self.categories)

    def crawl_key(self) -> str:
        cats = ",".join(self.categories) or "*"
        if self.start_url:
            return f"url|{self.start_url}|{cats}"
        return f"{self.sort}|{cats}"


def parse_categories(value: str | list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    """
    Parses a given value into a tuple of categories. The input can be a string, a list of strings,
    or a tuple of strings. It ensures that all parsed categories are valid, case-insensitive,
    and free of duplicates. If the input includes any unknown categories, an exception is raised.

    :param value: The value to parse; can be a single string, a list of strings, a tuple of strings,
        or None. If the input is None, returns an empty tuple.
    :type value: str | list[str] | tuple[str, ...] | None
    :return: A tuple containing unique, valid, and lowercased category names in their first
        encountered order.
    :rtype: tuple[str, ...]
    :raises ValueError: If the input contains unknown categories that are not part of the allowed
        CATEGORIES.
    """
    if not value:
        return ()
    raw = [value] if isinstance(value, str) else list(value)
    parts: list[str] = []
    for item in raw:
        parts.extend(piece.strip().lower() for piece in item.split(","))
    unknown = [part for part in parts if part and part not in CATEGORIES]
    if unknown:
        raise ValueError(
            "unknown category: "
            + ", ".join(unknown)
            + f" (choose from {', '.join(CATEGORIES)})"
        )
    seen: set[str] = set()
    ordered: list[str] = []
    for part in parts:
        if not part or part in seen:
            continue
        seen.add(part)
        ordered.append(part)
    return tuple(ordered)


def load_config(
        *,
        cli: Mapping[str, Any] | None = None,
        environ: Mapping[str, str] | None = None,
        config_path: str | Path | None = None,
        cwd: Path | None = None,
) -> RunConfig:
    """
    Loads the configuration for the application by merging settings from multiple sources
    in the following order of precedence (highest to lowest):
    1. Command-line arguments (`cli`)
    2. Environment variables (`environ`)
    3. Configuration file (`config_path` or default file in `cwd`)
    4. Default values defined in `RunConfig`

    :param cli: Optional mapping of command-line arguments.
    :type cli: Mapping[str, Any] | None
    :param environ: Optional mapping of environment variables.
    :type environ: Mapping[str, str] | None
    :param config_path: Optional path to a configuration file.
    :type config_path: str | Path | None
    :param cwd: Optional current working directory to search for the default configuration file.
    :type cwd: Path | None
    :return: A `RunConfig` instance populated with the merged configuration settings.
    :rtype: RunConfig
    """
    root = cwd or Path.cwd()
    path = _resolve_config_path(config_path, root)
    config = RunConfig()
    if path is not None:
        config = _apply(config, _read_toml(path))
    config = _apply(config, _from_env(environ if environ is not None else os.environ))
    if cli:
        config = _apply(config, dict(cli))
    return config


def _resolve_config_path(config_path: str | Path | None, cwd: Path) -> Path | None:
    """
    Resolve the configuration file path based on the provided config_path or the default
    config file in the current working directory.

    If a `config_path` is provided, checks whether the file exists. If it does, the path
    is resolved and returned. If the `config_path` is invalid or does not exist, a
    FileNotFoundError is raised. If `config_path` is not provided, attempts to locate
    a default configuration file (`DEFAULT_CONFIG_NAME`) in the specified `cwd`.
    If the default file exists, its path is returned. If no valid configuration file
    is found, returns None.

    :param config_path: Optional path to a configuration file to resolve.
    :type config_path: str | Path | None
    :param cwd: The current working directory to search for the default
                 configuration file if `config_path` is None.
    :type cwd: Path
    :return: A valid resolved Path to the configuration file if found,
             or None if no valid path is resolved.
    :rtype: Path | None
    :raises FileNotFoundError: If `config_path` is provided but does not
                                lead to a valid file.
    """
    if config_path is not None:
        path = Path(config_path)
        if not path.is_file():
            raise FileNotFoundError(f"config file not found: {path}")
        return path
    candidate = cwd / DEFAULT_CONFIG_NAME
    return candidate if candidate.is_file() else None


def _read_toml(path: Path) -> dict[str, Any]:
    """

    """
    import tomllib

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if "database" in data and "database_path" not in data:
        data["database_path"] = data.pop("database")
    return data


def _from_env(environ: Mapping[str, str]) -> dict[str, Any]:
    """
    Parses and extracts configuration settings from environment variables into a dictionary format.
    This function maps specific environment variables to corresponding keys in the output dictionary,
    converting their values to appropriate types when necessary. It is designed to accommodate a wide
    range of configuration options, including base URLs, database paths, request delays, limits, sorting
    preferences, and various flags like dry run or verbose mode.

    :param environ: A mapping object that contains environment variables as key-value pairs. Typically,
                    this will be `os.environ` or a similar dictionary-like object.
    :type environ: Mapping[str, str]
    :return: A dictionary containing extracted configuration settings, where the keys correspond to
             specific application options and the values reflect the parsed and converted user-defined
             values from the environment variables.
    :rtype: dict[str, Any]
    """
    updates: dict[str, Any] = {}
    if environ.get("BASE_URL"):
        updates["base_url"] = environ["BASE_URL"]
    db = environ.get("DATABASE_PATH") or environ.get("DATABASE_FILE_PATH")
    if db:
        updates["database_path"] = db
    if environ.get("REQUEST_DELAY_SECONDS"):
        updates["delay"] = float(environ["REQUEST_DELAY_SECONDS"])
    if environ.get("AVHERALD_LIMIT"):
        updates["limit"] = int(environ["AVHERALD_LIMIT"])
    if environ.get("AVHERALD_SORT"):
        updates["sort"] = environ["AVHERALD_SORT"]
    if environ.get("AVHERALD_CATEGORIES"):
        updates["categories"] = environ["AVHERALD_CATEGORIES"]
    if environ.get("AVHERALD_MAX_PAGES"):
        updates["max_pages"] = int(environ["AVHERALD_MAX_PAGES"])
    if environ.get("AVHERALD_TIMEOUT"):
        updates["timeout"] = float(environ["AVHERALD_TIMEOUT"])
    if environ.get("AVHERALD_DRY_RUN"):
        updates["dry_run"] = _as_bool(environ["AVHERALD_DRY_RUN"])
    if environ.get("AVHERALD_VERBOSE"):
        updates["verbose"] = _as_bool(environ["AVHERALD_VERBOSE"])
    if environ.get("AVHERALD_RESUME"):
        updates["resume"] = _as_bool(environ["AVHERALD_RESUME"])
    if environ.get("AVHERALD_FRESH"):
        updates["fresh"] = _as_bool(environ["AVHERALD_FRESH"])
    proxy = environ.get("HTTPS_PROXY") or environ.get("https_proxy") or environ.get(
        "HTTP_PROXY"
    ) or environ.get("http_proxy")
    if proxy:
        updates["proxy"] = proxy
    return updates


def _as_bool(value: str) -> bool:
    """
    Converts a given string to its boolean equivalent based on specific textual values.

    This function interprets a given string and returns a boolean value, evaluating
    it against a set of predefined text values that represent a truthy state.

    :param value: The string input to evaluate.
    :type value: str
    :return: The boolean equivalent of the input string. Returns True if the string
        matches any of {"1", "true", "yes", "on"} (case insensitive), otherwise False.
    :rtype: bool
    """
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _apply(config: RunConfig, updates: Mapping[str, Any]) -> RunConfig:
    """
    Applies the updates to an existing RunConfig object by filtering and converting
    provided values according to the constraints and required formats. Only allowed
    fields in the RunConfig object are updated. Types and values of attributes are
    validated and transformed as needed.

    :param config: The original RunConfig object to update.
    :type config: RunConfig
    :param updates: A mapping of key-value pairs representing the updates to apply
        to the RunConfig object. Unrecognized keys or values set to None are ignored.
    :type updates: Mapping[str, Any]
    :return: A new RunConfig object with the updates applied.
    :rtype: RunConfig

    :raises ValueError: If an invalid value is provided for the "sort" attribute.
        The value must be either "update" or "occurrence".
    """
    allowed = set(RunConfig.__dataclass_fields__)
    cleaned: dict[str, Any] = {}
    for key, value in updates.items():
        if key not in allowed or value is None:
            continue
        cleaned[key] = value
    if "categories" in cleaned:
        cleaned["categories"] = parse_categories(cleaned["categories"])
    if "database_path" in cleaned:
        cleaned["database_path"] = Path(cleaned["database_path"])
    if "base_url" in cleaned:
        cleaned["base_url"] = str(cleaned["base_url"]).rstrip("/")
    if "sort" in cleaned:
        sort = str(cleaned["sort"]).lower()
        if sort not in ("update", "occurrence"):
            raise ValueError("sort must be 'update' or 'occurrence'")
        cleaned["sort"] = sort
    if "max_pages" in cleaned:
        pages = int(cleaned["max_pages"])
        cleaned["max_pages"] = pages if pages > 0 else None
    if "limit" in cleaned:
        cleaned["limit"] = int(cleaned["limit"])
    if "delay" in cleaned:
        cleaned["delay"] = float(cleaned["delay"])
    if "timeout" in cleaned:
        cleaned["timeout"] = float(cleaned["timeout"])
    for flag in ("dry_run", "verbose", "quiet", "resume", "fresh"):
        if flag in cleaned and not isinstance(cleaned[flag], bool):
            cleaned[flag] = _as_bool(str(cleaned[flag]))
    return replace(config, **cleaned)
