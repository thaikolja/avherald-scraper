# The Aviation Herald Scraper

![GitLab Release](https://img.shields.io/gitlab/v/release/thaikolja%2Favherald-scraper) ![GitLab Stars](https://img.shields.io/gitlab/stars/thaikolja%2Favherald-scraper?style=flat&label=gitlab%20stars) ![GitLab Forks](https://img.shields.io/gitlab/forks/thaikolja%2Favherald-scraper?style=flat&label=gitlab%20forks) ![GitHub Repo stars](https://img.shields.io/github/stars/thaikolja/avherald-scraper?style=flat&label=github%20stars) ![GitHub forks](https://img.shields.io/github/forks/thaikolja/avherald-scraper?style=flat&label=github%20forks)

**[The Aviation Herald](https://avherald.com/)** is a website [registered](https://avherald.com/h?impressum=) to the Austrian NOMIS SOFT Data Processing Limited Liability Company that documents aviation accidents and incidents. It's known for its detailed reports, often compiled from various sources. This Python 3 script can be used to extract data from the website by scraping.

## Description

### Scraping

Since avherald.com does not have a [RESTful API](https://aws.amazon.com/what-is/restful-api/), [RSS Feed](https://support.microsoft.com/en-us/office/what-are-rss-feeds-e8aaebc3-a0a7-40cd-9e10-88f9c1e74b97), or other ways to get data without visiting the website, this Python 3 script will extract the data for you using [website scraping](https://www.parsehub.com/blog/what-is-web-scraping/).

Adjust the number of pages in the code at `MAX_PAGES_TO_SCRAPE` to avoid getting blocked immediately. A `REQUEST_DELAY_SECONDS` of `1` second is also a good way to avoid DDoS-lookalike requests, quickly leading to a ban on your IP address.

### Saving

This script stores the information it gathers in an [SQLite database](https://www.simplilearn.com/tutorials/sql-tutorial/what-is-sqlite) called `data.sqlite`. You can set up a CRON job to run this script every 24 hours with `MAX_PAGES_TO_SCRAPE` set to `1`. The script will gather the latest data from the first page while ignoring duplicates.

## Copyright

The Aviation Herald has a copyright protecting its data, stating:

> © 2008-2025 by The Aviation Herald, all rights reserved, reproduction, redistribution and AI learning/use prohibited.

Please be aware of the limitations. This script is, therefore, a **proof of concept** and is **only meant for educational purposes**.

## Usage

To set up the script, use the following steps:

1. `git clone https://gitlab.com/thaikolja/avherald-scraper.git`
2. `cd avherald-scraper`
3. `python3 -m venv venv`
4. `source venv/bin/activate`
5. `pip install -r requirements.txt`
6. Adjust `MAX_PAGES_TO_SCRAPE`, `REQUEST_DELAY_SECONDS`, and `DATABASE_FILE`
7. Run `python avherald-scraper/main.py`

## License

**The Python code itself is licensed under MIT.**

The [MIT License](https://choosealicense.com/licenses/mit/) is a permissive free software license that grants you the freedom to use, modify, and distribute the software, even for commercial purposes. You can do whatever you want with the code as long as you include the original copyright notice and the license text in your distribution.

## Authors

* Kolja Nolte <kolja.nolte@gmail.com>

