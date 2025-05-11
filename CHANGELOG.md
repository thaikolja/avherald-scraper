# Changelog

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
