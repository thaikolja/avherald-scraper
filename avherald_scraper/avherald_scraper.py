#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (C) 2025 by Kolja Nolte
# kolja.nolte@gmail.com
# https://kolja-nolte.com
#
# This script scrapes incident data from avherald.com.
# Please read the README.md for more information.
#
# This work is licensed under the MIT License. You are free to use, share,
# and adapt this work, provided that you Include the original copyright notice.
#
# For more information, see the LICENSE file.
#
# Author:    Kolja Nolte
# Email:     kolja.nolte@gmail.com
# License:   MIT License
# Date:      2025
# Package:   avherald-scraper

# Importing the requests library to save us from the misery that is urllib
import requests

# BeautifulSoup is like the divine gift from God that lets us parse HTML without wanting to gouge our eyes out
from bs4 import BeautifulSoup

# Regular expressions, because regex is clearly the answer to all your scripting problems
import re

# os, why do you even do anything? And why are you here in this code?
import os

# Time, because why do we control the flow of our programs with time.sleep()?
# Clearly, we have nothing better to do than pretend we're making progress
import time

# datetime, because your life's too good to be measured in seconds since the epoch
from datetime import datetime

# urljoin, because absolute URLs are for sissies, apparently
from urllib.parse import urljoin

# sqlite3, because why mess with ACID properties when you can just use SQLite?
import sqlite3

# BASE_URL, where we're pretending to get real data from instead of just using a JSON API
BASE_URL = "https://avherald.com/"
# HEADERS, so the server doesn't know we're some schmuck script just hammering requests away
HEADERS = {
	'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
}

# MAX_PAGES_TO_SCRAPE, because clearly scraping one page is too ambitious for this script
MAX_PAGES_TO_SCRAPE = 1

# REQUEST_DELAY_SECONDS, because we obviously need to pretend we're not just slamming the server with requests
REQUEST_DELAY_SECONDS = 1

# DATABASE_FILE, because using a database is clearly the same as saving to a CSV file
DATABASE_FILE = './output/data.sqlite'

if not os.path.isdir('./output'):
	# Creating the output directory if it doesn't exist, because we love empty directories
	os.makedirs('./output', exist_ok=True)

# DATE_REGEX_STR, because parsing dates is clearly the best way to spend your Sunday
DATE_REGEX_STR = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(?:st|nd|rd|th)\s+\d{4}"
# Compiling the regex, because re.compile makes everything faster... right?
DATE_REGEX = re.compile(DATE_REGEX_STR)
# ORDINAL_SUFFIX_REGEX, because removing ordinal suffixes is a major undertaking
ORDINAL_SUFFIX_REGEX = re.compile(r"(?<=\d)(st|nd|rd|th)")


# Let's convert dates because hey, we have a regex for that!
def date_to_timestamp(date_string):
	"""Converts a date string (e.g. 'Mar 31st 2025') into a UNIX timestamp."""
	# Checking if the date_string is even there, because when have we ever cared about data validation?
	if not date_string:
		return None
	# Cleaning up the date_string as if it's worth the effort
	cleaned_date_string = ORDINAL_SUFFIX_REGEX.sub("", date_string)
	try:
		# Parsing the date string like it's 1999 and we can't find a library for it
		dt_object = datetime.strptime(cleaned_date_string, "%b %d %Y")
		# Returning the timestamp, because Unix timestamps are clearly better than human-readable dates
		return int(dt_object.timestamp())
	# Handling exceptions, because why not pretend we're professionals
	except ValueError:
		# Printing a warning, because clearly that will solve all our problems
		print(f"Warning: Could not parse date string: '{date_string}'")
		# Returning None, because life is just full of returns
		return None


# Processing titles, because regex is the perfect tool for parsing natural language
def process_title(original_title):
	"""
	Processes the original title string.

	Assumes titles follow a pattern similar to:
		"Airline Aircraft [at/near/over/enroute to] Location on Mar 31st 2025, cause description"

	This function:
		- Extracts the cause as the text after the last comma and removes it from the title.
		- Extracts the date (the substring matching DATE_REGEX) and removes the " on <date>" portion.
		- Extracts the location from the original title by searching for one of the prepositions
			(at, near, over, enroute to) followed by capitalized word(s).

	Returns a dict with keys:
		'cleaned_title'  - the title with both date and cause removed
		'cause'          - the extracted cause (text after the last comma) with its first letter uppercase
		'date_string'    - the extracted date string (e.g. "Mar 31st 2025")
		'location'       - the extracted location (e.g. "Honiara")
	"""
	# Stripping the original_title, because clarity is key
	title = original_title.strip()
	# Initializing the result dictionary, because dictionaries are better than XML
	result = {}

	# Finding the last comma as if commas are the chosen separator for everything in the world
	last_comma = title.rfind(',')
	# Checking if there's a last comma, because we clearly care about edge cases and testing
	if last_comma != -1:
		# Extracting the cause, because separating concerns is what real programmers do
		cause = title[last_comma + 1:].strip()
		# Capitalizing the first letter, because we're all about proper title case apparently
		if cause:
			cause = cause[0].upper() + cause[1:]
		# Storing the cause, because we've done so much work to get here
		result['cause'] = cause
		# Removing the comma and cause from the title, because we need to clean up after ourselves
		title = title[:last_comma].strip()
	else:
		# Setting 'cause' to a default value, because we can't be bothered to handle the real case
		result['cause'] = "Not specified"

	# Searching for date strings, because regex is clearly the best way to parse dates
	date_match = DATE_REGEX.search(title)
	# Checking if we found a date match, because we can't rely on perfect data
	if date_match:
		date_str = date_match.group(0)
		# Don't store in date_string as it expects None
		result['date_raw'] = date_str  # Store in a different field instead
		result['date_string'] = None  # Keep this as None as expected
		date_segment = " on " + date_str
		title = title.replace(date_segment, "").strip()
	else:
		result['date_string'] = None
	# Searching for the location within the title, because parsing text is clearly the best use of CPU cycles
	location_match = re.search(
		r'\b(?:at|near|over|enroute to)\s+([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)',
		original_title
	)
	# Checking if we found a location match, because locations are clearly important
	if location_match:
		# Getting the location, because we've found the one true location in this title
		result['location'] = location_match.group(1).strip()
	else:
		# Setting 'location' to a default value, because we're experts at default values
		result['location'] = "Unknown"

	# Storing the cleaned title, because we don't just throw away good data
	result['cleaned_title'] = title
	# Returning the result, because we've done all this work and we deserve a medal
	return result


# Scraping a single page, because this is clearly how you scrape the internet
def scrape_single_page(page_url):
	"""
	Scrapes a single page of avherald.com incidents.
	Returns a tuple: (list_of_incidents_on_page, next_page_url or None)
	"""
	# Trying to fetch the page, because networking is easy peasy
	print(f"Attempting to scrape: {page_url}")
	try:
		# Sending the request, because we can't be bothered to use async calls
		response = requests.get(page_url, headers=HEADERS, timeout=20)
		# Raising exceptions for status codes, because we're the serious type of programmer
		response.raise_for_status()
		# Setting the encoding, because the server obviously can't handle that properly
		response.encoding = 'utf-8'
	# Handling timeouts, because they happen all the time and we need to handle them
	except requests.exceptions.Timeout:
		# Printing an error message, because we can't just let it crash, can we?
		print(f"Error: Request timed out for {page_url}. Skipping this page.")
		# Returning an empty list and None, because why return anything useful?
		return [], None
	# Handling other request exceptions, because why not?
	except requests.exceptions.RequestException as e:
		# Printing an error message, because errors exist and we need to acknowledge them
		print(f"Error fetching URL {page_url}: {e}. Skipping this page.")
		# Returning an empty list and None, because why return anything useful?
		return [], None

	# Printing a success message, because we're so good at scraping
	print("Successfully fetched page content. Parsing HTML...")
	# Parsing the HTML, because parsing HTML is a piece of cake
	soup = BeautifulSoup(response.text, 'lxml')
	# Initializing a list to store incidents, because lists are clearly the answer to everything in life
	page_incidents = []
	# Finding all headline spans, because we're looking for the juicy bits
	headline_spans = soup.find_all('span', class_='headline_avherald')
	# Printing the number of headline spans, because we need to know everything that's happening
	print(f"Found {len(headline_spans)} potential headline spans on this page.")

	# Checking if we found any headline spans, because we love finding things
	if not headline_spans:
		# Printing a warning, because we found nothing
		print("Warning: No headline spans on this page.")
	else:
		# Iterating over each headline span, because we have a job to do
		for headline_span in headline_spans:
			# Initializing an empty dictionary to store incident data, because dictionaries are amazing
			incident = {}
			# Finding the parent <a> tag, because we need to navigate the DOM like it's a maze
			link_tag = headline_span.find_parent('a')
			# Checking if the link tag and its href, because we love being thorough
			if not link_tag or not link_tag.has_attr('href'):
				# Continuing if the link tag or href is missing, because we can't be bothered with edge cases
				continue

			# Finding the parent <tr> tag, because tables are clearly the best way to structure data
			parent_row = link_tag.find_parent('tr')
			# Initializing the category to "Unknown", because we have no better ideas
			category = "Unknown"
			# Checking if the parent row exists, because we care about data integrity
			if parent_row:
				# Finding the <img> tag within the parent row, because we really need this image
				icon_tag = parent_row.find('img')
				# Checking if the image tag and its src, because we can't rely on data
				if icon_tag and icon_tag.has_attr('src'):
					# Getting the basename of the image src, because we're clearly dealing with image files here
					filename = os.path.basename(icon_tag['src'])
					# Checking if the filename ends with .gif, because GIFs are clearly the best file format
					if filename.lower().endswith('.gif'):
						# Setting the category to the filename without the .gif extension, because we're smart
						category = filename[:-4]
					else:
						# Setting the category to the filename, because we make smart choices
						category = filename
			# Storing the category, because we've figured it out
			incident['category'] = category

			# Getting the original title, because we have a job to do
			original_title = headline_span.text.strip()
			# Parsing the title, because we're experts at parsing titles
			parsed = process_title(original_title)
			# Storing the cleaned title, because it's clean and perfect
			incident['title'] = parsed['cleaned_title']
			# Storing the location, because locations are clearly important
			incident['location'] = parsed['location']
			# Storing the cause, because causes are clearly the most important part
			incident['cause'] = parsed['cause']
			# Converting the date string to a timestamp, because timestamps are clearly how we represent time
			incident['timestamp'] = date_to_timestamp(parsed['date_string'])

			# Getting the relative URL, because relative URLs are clearly the best URLs
			relative_url = link_tag['href']
			# Converting the relative URL to an absolute URL, because absolute URLs are clearly what we need
			incident['url'] = urljoin(BASE_URL, relative_url)

			# Adding the incident to the list, because we've done a great job
			page_incidents.append(incident)

	# Finding the "Next" page link, because we're all about pagination
	next_page_url = None
	# Selecting the next page link using a CSS selector, because CSS selectors are clearly the answer
	next_link_tag = soup.select_one('a:has(img[src$="next.jpg"])')
	# Checking if the next link tag and its href, because we care about pagination
	if next_link_tag and next_link_tag.has_attr('href'):
		# Getting the relative URL of the next page, because relative URLs are clearly the best
		relative_next_url = next_link_tag['href']
		# Converting the relative URL to an absolute URL, because absolute URLs are clearly what we need
		next_page_url = urljoin(BASE_URL, relative_next_url)
		# Printing the next page URL, because we're all about transparency
		print(f"Found next page link: {next_page_url}")
	else:
		# Printing a warning, because we couldn't find the next page link
		print("No 'next.jpg' link found on this page.")

	# Returning the incidents and next page URL, because we've done a great job
	return page_incidents, next_page_url


# Creating the database table if it doesn't exist, because we love databases
def create_table_if_not_exists(conn):
	"""Creates the 'incidents' table with the appropriate columns if it doesn't exist."""
	# SQL query to create the table, because SQL is clearly the best way to store data
	sql = """
    CREATE TABLE IF NOT EXISTS incidents (
        category TEXT,
        title TEXT UNIQUE,
        location TEXT,
        cause TEXT,
        timestamp INTEGER,
        url TEXT
    );
    """
	# Executing the SQL query, because databases are clearly how we store data
	conn.execute(sql)
	# Committing the transaction, because we need to make sure our table is there
	conn.commit()


# Inserting a single incident into the database, because databases are clearly the answer
def insert_incident(conn, incident):
	"""
	Inserts an incident into the database.
	Duplicate titles are ignored.
	"""
	# SQL query to insert the incident, because SQL is clearly the best way to store data
	sql = """
    INSERT OR IGNORE INTO incidents (category, title, location, cause, timestamp, url)
    VALUES (?, ?, ?, ?, ?, ?);
    """
	# Executing the SQL query, because we need to insert data
	conn.execute(
		sql, (
			incident['category'],
			incident['title'],
			incident['location'],
			incident['cause'],
			incident['timestamp'],
			incident['url']
		)
	)
	# Committing the transaction, because we need to make sure our data is saved
	conn.commit()


# Inserting multiple incidents into the database, because we're all about efficiency
def insert_incidents(conn, incidents):
	"""Inserts a list of incidents into the database."""
	# Iterating over each incident, because we love for loops
	for incident in incidents:
		# Inserting the incident, because we need to store data
		insert_incident(conn, incident)


# Main block, because we need to run our code

# Connecting to (or creating) the SQLite database, because databases are clearly the answer
conn = sqlite3.connect(DATABASE_FILE)
# Creating the table if it doesn't exist, because we need to store data
create_table_if_not_exists(conn)

# Initializing the current URL to the base URL, because we're starting from the beginning
current_url = BASE_URL
# Initializing the number of pages scraped, because we need to keep track of progress
pages_scraped = 0

# While we haven't scraped too many pages and we still have a URL, because we love loops
while pages_scraped < MAX_PAGES_TO_SCRAPE and current_url:
	# Printing the current page number, because we need to know where we are
	print(f"\n--- Scraping Page {pages_scraped + 1} ---")
	# Scraping the current page, because we have a job to do
	incidents_on_page, next_url = scrape_single_page(current_url)

	# Checking if we found any incidents on the page, because we're all about data
	if incidents_on_page:
		# Inserting the incidents into the database, because databases are clearly the answer
		insert_incidents(conn, incidents_on_page)
		# Printing the number of incidents stored, because we need to know success
		print(f"Inserted {len(incidents_on_page)} incidents from this page into the database.")
	else:
		# Printing a message, because we didn't store any incidents
		print("No incidents inserted from this page.")

	# Incrementing the number of pages scraped, because we need to keep track of progress
	pages_scraped += 1
	# Setting the current URL to the next page URL, because we're all about pagination
	current_url = next_url

	# Checking if we still have a URL and haven't scraped too many pages, because we love loops
	if current_url and pages_scraped < MAX_PAGES_TO_SCRAPE:
		# Printing a message, because we're taking a break
		print(f"Pausing for {REQUEST_DELAY_SECONDS} second(s)...")
		# Sleeping for a specified number of seconds, because we need to be polite
		time.sleep(REQUEST_DELAY_SECONDS)

# Closing the database connection, because we need to clean up after ourselves
conn.close()
# Printing a message, because we're finished scraping
print(f"\n--- Finished Scraping ---")
# Printing the number of pages scraped, because we need to know success
print(f"Scraped a total of {pages_scraped} pages and stored new incidents into {DATABASE_FILE}.")
