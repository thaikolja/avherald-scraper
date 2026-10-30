---
seo:
  title: The Aviation Herald Scraper
  description: Save Aviation Herald listing headlines to a file on your computer.
---

::u-page-hero
#title
The Aviation Herald Scraper

#description
A small command that copies listing headlines from The Aviation Herald into a file on your computer. It does not download the articles themselves.

#links
  :::u-button
  ---
  color: neutral
  size: xl
  to: /getting-started/introduction
  trailing-icon: i-lucide-arrow-right
  ---
  Get started
  :::

  :::u-button
  ---
  color: neutral
  size: xl
  to: /guide/examples
  variant: outline
  ---
  See examples
  :::
::

::u-page-section
#title
What it does

#features
  :::u-page-feature
  ---
  icon: i-lucide-list
  to: /guide/examples
  ---
  #title
  Keep a local list

  #description
  Store the headline, date, category, and link. Leave the article text on the website.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-play
  to: /getting-started/first-run
  ---
  #title
  Run it again tomorrow

  #description
  The next run continues where the last one stopped and skips headlines you already have.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-file-output
  to: /guide/output
  ---
  #title
  Choose the file

  #description
  SQLite by default. Also JSON, CSV, Excel, or a short printout in the terminal.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-shield
  to: /project/legal
  ---
  #title
  Stay small

  #description
  The crawl waits between pages, names itself in the User-Agent, and does not pretend to be a browser.
  :::
::
