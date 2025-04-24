# ✈️ The Aviation Herald Scraper

[![GitLab Release](https://img.shields.io/gitlab/v/release/thaikolja%2Favherald-scraper)](https://gitlab.com/thaikolja/avherald-scraper/-/releases) [![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/downloads/) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![GitLab Stars](https://img.shields.io/gitlab/stars/thaikolja%2Favherald-scraper?style=flat&label=gitlab%20stars)](https://gitlab.com/thaikolja/avherald-scraper) [![GitHub Repo stars](https://img.shields.io/github/stars/thaikolja/avherald-scraper?style=flat&label=github%20stars)](https://github.com/thaikolja/avherald-scraper)

**The Aviation Herald Scraper** is a Python tool designed to automatically extract basic incident information from the front page headlines of [avherald.com](https://avherald.com/). Since the website does not offer a public API or RSS feed, this script uses web scraping techniques to gather data. **There is strictly no AI usage in this project**.

**Important Note on Copyright:** This script *only* parses the headlines and associated metadata (see "Features" below) visible on the main page(s) under the [Fair Use doctrine](https://en.wikipedia.org/wiki/Fair_use). To respect the website's copyright notice, **it does not scrape the full content of the linked incident reports**. The metadata is stored locally in an SQLite database.

## 📜 Disclaimer & Copyright

**[The Aviation Herald](https://avherald.com/)** has a strict copyright notice:

> © 2008-2025 by The Aviation Herald, all rights reserved, reproduction, redistribution and AI learning/use prohibited.

This script is provided as a **proof of concept** and is intended **only for educational purposes**. Please be mindful of [avherald.com's terms of service](https://avherald.com/h?impressum=) and use this script responsibly. The scraped data should not be redistributed or used for commercial purposes or AI training without permission from The Aviation Herald.

## 🚀 Features

*   **📰 Headline Scraping**: Extracts incident headlines from the avherald.com front page.
*   **📊 Data Extraction**: Parses key details from headlines:
    *   Incident Category (e.g., `crash`, `incident`, `news`)
    *   Cleaned Title
    *   Approximate Location (if mentioned)
    *   Suspected Cause/Type (if mentioned)
    *   Incident Date (converted to timestamp)
    *   Direct URL to the full report on avherald.com
*   **💾 Local Storage**: Saves extracted data into a local SQLite database (`./output/data.sqlite` by default).
*   **🚫 Duplicate Prevention**: Avoids adding duplicate entries based on the incident title.
*   **⚙️ Configurable**: Allows easy configuration of:
    *   Number of pages to scrape (`MAX_PAGES_TO_SCRAPE`).
    *   Delay between page requests (`REQUEST_DELAY_SECONDS`) to avoid overloading the server.
    *   Database file path (`DATABASE_FILE`).
    *   Verbosity (`SHOW_DETAILS`).
*   **🤖 Polite Scraping**: Includes a user-agent header and configurable delay.

## 🛠️ Installation

Follow these steps to set up and install the necessary dependencies. This guide assumes you have Python 3.8+ and `git` installed.

1.  **Clone the Repository:**
    Get the code from the main GitLab repository.
```bash
git clone https://gitlab.com/thaikolja/avherald-scraper.git
cd avherald-scraper
```

2.  **Create a Virtual Environment:**
    It's highly recommended to use a virtual environment to keep dependencies isolated.
    
```bash
# Create the environment (use python3 if python points to Python 2)
python -m venv venv
```

3.  **Activate the Virtual Environment:**
    1.  On **macOS/Linux**:
```bash
source venv/bin/activate
```

You should see `(venv)` at the beginning of your terminal prompt.

4.  **Install Dependencies:**
    Install all required Python packages listed in `requirements.txt`.
    ```bash
    pip install -r requirements.txt
    ```

## ⚙️ Configuration

Before running the script, you can adjust its behavior by editing the constants at the top of the `main.py` file:

*   `MAX_PAGES_TO_SCRAPE`: (*int*) How many pages of avherald.com to scrape[^1] (e.g., `1` for only the front page, `3` for the first three pages). **Default**: `1`.
*   `REQUEST_DELAY_SECONDS`: (*int*) Number of seconds to wait between fetching pages. Helps prevent getting blocked. **Default**: `3`.
*   `DATABASE_FILE`: (*string*) Path where the SQLite database file will be created/updated. **Default**: `'./output/data.sqlite'`.
*   `SHOW_DETAILS`: (*bool*) Set to `True` to print detailed progress messages during scraping, or `False` to run silently. **Default**: `False`.

## ▶️ Usage

Once installed and configured, run the scraper from the project's root directory:

```bash
python main.py
```

### Under the Hood

The script will:

1.  Connect to (or create) the SQLite database specified in `DATABASE_FILE`.
2.  Create the `incidents` table if it doesn't exist.
3.  Using Python's [Beautiful Soup library](https://pypi.org/project/beautifulsoup4/), start scraping from the [avherald.com](https://avherald.com/) homepage.
4.  Fetch and parse headlines for the number of pages specified by `MAX_PAGES_TO_SCRAPE`, pausing between pages according to `REQUEST_DELAY_SECONDS`.
5.  Insert any *new* incidents found into the database. Duplicates (based on title) will be ignored.
6.  Print progress if `SHOW_DETAILS` is `True`.

### Example: Daily Update Cron Job

You can set up a cron job (on Linux/macOS) or a scheduled task (on Windows) to run the script once every 24 hours (recommended) and only fetch the latest incidents from the front page, thus reducing unnecessary server load for avherald.com's servers.

1.  Edit `main.py` and set `MAX_PAGES_TO_SCRAPE = 1`.
2.  [Set up a cron job](https://phoenixnap.com/kb/set-up-cron-job-linux) to execute the `python main.py` command using the correct **absolute paths** for your Python executable (within the `venv/bin` directory) and the script.

## 🧪 Testing

If you use CI/CD pipelines, you should use `pytest` to check if the code works as expected. For that, run the following command from the root directory:

```bash
pytest tests/
```

The expected output should be:

```bash
 ===== 9 passed in 0.15s =====
```

## 👨‍💻 Author

1.  **Kolja Nolte** <kolja.nolte@gmail.com>

## 🤝 Contributing

Contributions are welcome! If you'd like to improve the scraper, please follow these steps. **You can do this either on GitLab or GitHub.**

1.  Fork the project on GitLab: [https://gitlab.com/thaikolja/avherald-scraper](https://gitlab.com/thaikolja/avherald-scraper)
2.  Create your feature branch: `git checkout -b feature/AmazingFeature`
3.  Commit your changes: `git commit -m 'Add some AmazingFeature'`
4.  Push to the branch: `git push origin feature/AmazingFeature`
5.  Open a Merge Request on GitLab.

Please ensure your code adheres to the existing style and includes relevant documentation or tests if applicable.

## 📜 License

The Python code for this project is licensed under the **MIT License**. See the `LICENSE` file for complete details.

This license **applies only to the code** itself, **not** to the data scraped from [avherald.com](https://avherald.com/), which remains subject to their copyright.

## 🙏 Acknowledgements

*   **[The Aviation Herald](https://avherald.com/)**: For providing the valuable incident data.
*   **[Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/)**: For HTML parsing.
*   **[Requests](https://requests.readthedocs.io/)**: For handling HTTP requests.
*   **[lxml](https://lxml.de/)**: For efficient XML and HTML parsing.

---
[^1]: Use this option responsibly to avoid unnecessary traffic for avherald.com's servers and not to get your IP address banned.

