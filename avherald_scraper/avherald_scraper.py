# -*- coding: utf-8 -*-
"""
This script scrapes incident data from avherald.com.

It includes functions for scraping, parsing, and storing incident data in a SQLite database.

Copyright (C) 2025 by Kolja Nolte
kolja.nolte@gmail.com
https://www.kolja-nolte.com

This work is licensed under the MIT License. You are free to use, share,
and adapt this work, provided that you Include the original copyright notice.

For more information, see the LICENSE file.

Author:    Kolja Nolte
Email:     kolja.nolte@gmail.com
License:   MIT License
Date:      2025
Package:   avherald-scraper
"""

# Import the requests library for making HTTP requests.
import requests

# Import the dotenv library for loading environment variables.
import dotenv

# Import the BeautifulSoup library for parsing HTML.
from bs4 import BeautifulSoup

# Import the regular expression library.
import re

# Import the operating system interface.
import os

# Import the time module.
import time

# Import datetime module.
from datetime import datetime

# Import the URL parsing functions.
from urllib.parse import urljoin

# Import the SQLite library.
import sqlite3

# Import calendar module for UTC timestamp.
import calendar

env_path = dotenv.find_dotenv('.env', True)

if not os.path.exists(env_path):
	raise FileNotFoundError(
		f"Could not find .env file."
		f"Please create one in the root directory based on the .env.example file."
	)

# Load environment variables from a .env file.
dotenv.load_dotenv(env_path)

# List of required keys from the .env file
required_keys = [
	"BASE_URL",
	"DATABASE_FILE_PATH"
]

# Check that all required keys are set
missing_keys = [key for key in required_keys if not os.getenv(key)]
if missing_keys:
	raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_keys)}")

# Define the base URL for avherald.com.
BASE_URL = os.getenv("BASE_URL")

# Define the path to the SQLite database file.
DATABASE_FILE_PATH = os.getenv("DATABASE_FILE_PATH")

# Define the regular expression string for matching dates.
DATE_REGEX_STR = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(?:st|nd|rd|th)\s+\d{4}"

# Compile the date regular expression.
DATE_REGEX = re.compile(DATE_REGEX_STR)

# Compile the regular expression for removing ordinal suffixes.
ORDINAL_SUFFIX_REGEX = re.compile(r"(?<=\d)(st|nd|rd|th)")

# Create the output directory from the database file path.
output_directory = os.path.dirname(DATABASE_FILE_PATH)

# Check if the output directory exists.
if not os.path.isdir(output_directory):
	# Create the output directory if it doesn't exist, allowing intermediate directories to be created.
	os.makedirs(output_directory, exist_ok=True)


#
# Converts a date string (e.g. 'Mar 31st 2025') into a UNIX timestamp.
#
# @param date_string The date string to convert.
# @param show_details Whether to print details if parsing fails.
# @return The UNIX timestamp or None if parsing fails.
def date_to_timestamp(date_string, show_details=False):
	# Check if the date string is empty.
	if not date_string:
		# Return None if the date string is empty.
		return None
	# Remove ordinal suffixes from the date string.
	cleaned_date_string = ORDINAL_SUFFIX_REGEX.sub("", date_string)
	# Try to convert the cleaned date string to a timestamp.
	try:
		# Parse the cleaned date string into a datetime object.
		dt_object = datetime.strptime(cleaned_date_string, "%b %d %Y")
		# Convert the datetime object to a UNIX timestamp and return it.
		return calendar.timegm(dt_object.timetuple())
	# Catch a ValueError if the date string cannot be parsed.
	except ValueError:
		# Check if details should be shown.
		if show_details:
			# Print a warning message if the date string could not be parsed.
			print(f"Warning: Could not parse date string: '{date_string}'")
		# Return None if parsing fails.
		return None


#
# Processes the original title string.
#
# @param original_title The original title string to process.
# @param show_details Whether to print details if parsing fails.
# @return A dict with keys: 'cleaned_title', 'cause', 'date_string', 'location'
def process_title(original_title, show_details=False):
	# Strip leading/trailing whitespace from the title.
	title = original_title.strip()
	# Initialize the result dictionary.
	result = {}

	# Find the last comma in the title.
	last_comma = title.rfind(',')
	# Check if a comma was found.
	if last_comma != -1:
		# Extract the cause from the title.
		cause = title[last_comma + 1:].strip()
		# Check if the cause is not empty.
		if cause:
			# Capitalize the first letter of the cause.
			cause = cause[0].upper() + cause[1:]
		# Add the cause to the result dictionary.
		result['cause'] = cause
		# Update the title to exclude the cause.
		title = title[:last_comma].strip()
	# If no comma was found.
	else:
		# Set the cause to "Not specified".
		result['cause'] = "Not specified"

	# Search for a date in the title.
	date_match = DATE_REGEX.search(title)
	# Check if a date was found.
	if date_match:
		# Extract the date string.
		date_str = date_match.group(0)
		# Convert the date string to a timestamp.
		result['timestamp'] = date_to_timestamp(date_str, show_details=show_details)
		# Create a date segment string to remove from the title.
		date_segment = " on " + date_str
		# Remove the date segment from the title.
		title = title.replace(date_segment, "").strip()
	# If no date was found.
	else:
		# Set the timestamp to None.
		result['timestamp'] = None

	# Search for a location in the original title.
	location_match = re.search(
		r'\b(?:at|near|over|enroute to)\s+([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)',
		original_title
	)
	# Check if a location was found.
	if location_match:
		# Extract the location.
		result['location'] = location_match.group(1).strip()
	# If no location was found.
	else:
		# Set the location to "Unknown".
		result['location'] = "Unknown"

	# Set the cleaned title in the result dictionary.
	result['cleaned_title'] = title
	# Return the result dictionary.
	return result


#
# Scrapes a single page of avherald.com incidents.
#
# @param page_url The URL of the page to scrape.
# @param show_details Whether to print details during scraping.
# @return A tuple: (list_of_incidents_on_page, next_page_url or None)
def scrape_single_page(page_url, show_details=False):
	# Check if details should be shown.
	if show_details:
		# Print the URL being scraped.
		print(f"Attempting to scrape: {page_url}")

	# Try to fetch the page content.
	try:
		# Define the headers to be sent with the request, mimicking a browser.
		headers = {
			'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
		}

		# Make a GET request to the page URL with specified headers and timeout.
		response = requests.get(page_url, headers=headers, timeout=20)

		# Raise an exception for bad status codes.
		response.raise_for_status()

		# Set the encoding to utf-8.
		response.encoding = 'utf-8'

	# Catch a Timeout exception.
	except requests.exceptions.Timeout:
		# Check if details should be shown.
		if show_details:
			# Print an error message if the request timed out.
			print(f"Error: Request timed out for {page_url}. Skipping this page.")
		# Return an empty list and None for the next page URL.
		return [], None
	# Catch any other request exception.
	except requests.exceptions.RequestException as e:
		# Check if details should be shown.
		if show_details:
			# Print an error message if there was an error fetching the URL.
			print(f"Error fetching URL {page_url}: {e}. Skipping this page.")
		# Return an empty list and None for the next page URL.
		return [], None

	# Check if details should be shown.
	if show_details:
		# Print a message indicating that the page content was successfully fetched.
		print("Successfully fetched page content. Parsing HTML...")
	# Parse the HTML content using BeautifulSoup.
	soup = BeautifulSoup(response.text, 'lxml')
	# Initialize an empty list to store incidents found on the page.
	page_incidents = []
	# Find all headline spans on the page.
	headline_spans = soup.find_all('span', class_='headline_avherald')

	# Check if details should be shown.
	if show_details:
		# Print the number of potential headline spans found.
		print(f"Found {len(headline_spans)} potential headline spans on this page.")

	# Check if no headline spans were found.
	if not headline_spans:
		# Check if details should be shown.
		if show_details:
			# Print a warning message if no headline spans were found.
			print("Warning: No headline spans found on this page.")
	# If headline spans were found.
	else:
		# Iterate over each headline span.
		for headline_span in headline_spans:
			# Initialize an empty dictionary to store incident details.
			incident = {}
			# Find the parent <a> tag of the headline span.
			link_tag = headline_span.find_parent('a')
			# Check if the <a> tag exists and has an 'href' attribute.
			if not link_tag or not link_tag.has_attr('href'):
				# Skip to the next iteration if the <a> tag is missing or invalid.
				continue

			# Find the parent <tr> tag of the link tag.
			parent_row = link_tag.find_parent('tr')
			# Initialize the category to "Unknown".
			category = "Unknown"
			# Check if the parent row exists.
			if parent_row:
				# Find the <img> tag within the parent row.
				icon_tag = parent_row.find('img')
				# Check if the <img> tag exists and has a 'src' attribute.
				if icon_tag and icon_tag.has_attr('src'):
					# Extract the filename from the 'src' attribute.
					filename = os.path.basename(icon_tag['src'])
					# Check if the filename ends with '.gif' (case-insensitive).
					if filename.lower().endswith('.gif'):
						# Set the category to the filename without the '.gif' extension.
						category = filename[:-4]
					# Otherwise.
					else:
						# Set the category to the filename.
						category = filename
			# Set the category in the incident dictionary.
			incident['category'] = category

			# Extract the original title from the headline span and strip whitespace.
			original_title = headline_span.text.strip()
			# Process the title to extract relevant information.
			parsed = process_title(original_title, show_details=show_details)
			# Set the cleaned title in the incident dictionary.
			incident['title'] = parsed['cleaned_title']
			# Set the location in the incident dictionary.
			incident['location'] = parsed['location']
			# Set the cause in the incident dictionary.
			incident['cause'] = parsed['cause']
			# Set the timestamp in the incident dictionary.
			incident['timestamp'] = parsed['timestamp']

			# Extract the relative URL from the <a> tag.
			relative_url = link_tag['href']
			# Create the absolute URL by joining the base URL and the relative URL.
			incident['url'] = urljoin(BASE_URL, relative_url)

			# Add the incident dictionary to the list of page incidents.
			page_incidents.append(incident)

	# Initialize the next page URL to None.
	next_page_url = None
	# Find the next page link.
	next_link_tag = soup.select_one('a:has(img[src$="next.jpg"])')
	# Check if the next page link exists and has an 'href' attribute.
	if next_link_tag and next_link_tag.has_attr('href'):
		# Extract the relative URL from the next page link.
		relative_next_url = next_link_tag['href']
		# Create the absolute URL for the next page.
		next_page_url = urljoin(BASE_URL, relative_next_url)
		# Check if details should be shown.
		if show_details:
			# Print the next page URL.
			print(f"Found next page link: {next_page_url}")
	# If no next page link was found.
	else:
		# Check if details should be shown.
		if show_details:
			# Print a message indicating that no next page link was found.
			print("No 'next.jpg' link found on this page.")

	# Return the list of incidents and the next page URL.
	return page_incidents, next_page_url


#
# Creates the 'incidents' table with the appropriate columns if it doesn't exist.
#
# @param conn The database connection object.
def create_table_if_not_exists(conn):
	# Define the SQL query to create the 'incidents' table if it doesn't exist.
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
	# Execute the SQL query.
	conn.execute(sql)
	# Commit the changes to the database.
	conn.commit()


#
# Insert an incident into the database.
#
# @param conn The database connection object.
# @param incident The incident data to insert.
# @return True if a row was inserted, False otherwise.
def insert_incident(conn, incident):
	# Skip incidents with the category "news"
	if incident['category'].lower() == "news":
		# Returns False if the category is new.
		return False

	# Define the SQL query to insert an incident into the database, ignoring duplicates.
	sql = """
    INSERT OR IGNORE INTO incidents (category, title, location, cause, timestamp, url)
    VALUES (?, ?, ?, ?, ?, ?);
    """
	# Execute the SQL query with the incident data.
	cur = conn.execute(
		sql, (
			incident['category'],
			incident['title'],
			incident['location'],
			incident['cause'],
			incident['timestamp'],
			incident['url']
		)
	)
	# Commit the changes to the database.
	conn.commit()
	# Return True if a row was inserted, False otherwise.
	return cur.rowcount == 1  # True if inserted, False if skipped


#
# Inserts a list of incidents into the database.
#
# @param conn The database connection object.
# @param incidents A list of incident dictionaries to insert.
# @return A tuple: (inserted_count, skipped_count)
def insert_incidents(conn, incidents):
	# Initialize the inserted count.
	inserted = 0
	# Initialize the skipped count.
	skipped = 0
	# Iterate over each incident in the list.
	for incident in incidents:
		# Insert the incident into the database.
		if insert_incident(conn, incident):
			# Increment the inserted count if the incident was inserted.
			inserted += 1
		# If the incident was skipped.
		else:
			# Increment the skipped count if the incident was skipped.
			skipped += 1
	# Return the inserted and skipped counts.
	return inserted, skipped


#
# Scrapes avherald.com for incident data and stores it in a database.
#
# @param max_pages_to_scrape The maximum number of pages to scrape.
# @param request_delay_seconds The delay in seconds between requests.
# @param database_file The path to the SQLite database file.
# @param show_details Whether to print details during scraping.
def scrape(max_pages_to_scrape=3, request_delay_seconds=3, show_details=True):
	# Connect to the SQLite database.
	conn = sqlite3.connect(DATABASE_FILE_PATH)
	# Create the 'incidents' table if it doesn't exist.
	create_table_if_not_exists(conn)
	# Set the initial URL to the base URL.
	current_url = BASE_URL
	# Initialize the pages scraped count.
	pages_scraped = 0

	# Loop while the number of pages scraped is less than the maximum and the current URL is not None.
	while pages_scraped < max_pages_to_scrape and current_url:
		# Check if details should be shown.
		if show_details:
			# Print the current page being scraped.
			print(f"\n--- Scraping Page {pages_scraped + 1} ---")
		# Scrape the current page.
		incidents_on_page, next_url = scrape_single_page(current_url, show_details=show_details)
		# Check if any incidents were found on the page.
		if incidents_on_page:
			# Insert the incidents into the database.
			inserted, skipped = insert_incidents(conn, incidents_on_page)
			# Check if details should be shown.
			if show_details:
				# Print the number of incidents inserted and skipped.
				print(f"Inserted {inserted} incidents from this page into the database.")
				print(f"Skipped {skipped} incidents (already in database).")
		# If no incidents were found on the page.
		else:
			# Check if details should be shown.
			if show_details:
				# Print a message indicating that no incidents were inserted.
				print("No incidents inserted from this page.")
		# Increment the pages scraped count.
		pages_scraped += 1
		# Set the current URL to the next URL.
		current_url = next_url
		# Check if there is a next URL and the number of pages scraped is less than the maximum.
		if current_url and pages_scraped < max_pages_to_scrape:
			# Check if details should be shown.
			if show_details:
				# Print a message indicating that the script is pausing.
				print(f"Pausing for {request_delay_seconds} second(s)...")
			# Pause for the specified delay.
			time.sleep(request_delay_seconds)
	# Close the database connection.
	conn.close()
	# Check if details should be shown.
	if show_details:
		# Print a message indicating that scraping is finished.
		print(f"\n--- Finished Scraping ---")
		# Print the total number of pages scraped.
		print(f"Scraped a total of {pages_scraped} pages and stored new incidents into {DATABASE_FILE_PATH}.")
