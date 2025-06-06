# -*- coding: utf-8 -*-

# Copyright (C) 2025 by Kolja Nolte
# kolja.nolte@gmail.com
# https://wwww.kolja-nolte.com
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
# Email:     kolja.nolte@email.com
# License:   MIT License
# Date:      2025
# Package:   avherald-scraper

"""
Module Docstring: main.py

This script serves as the entry point for scraping aviation accident data from AV Herald.
It configures and initiates the scraping process, allowing users to specify parameters
such as the maximum number of pages to scrape, the delay between requests, the database
file for storing the scraped data, and whether to display detailed output during the scraping.
"""

# Import the avherald_scraper module
from avherald_scraper import avherald_scraper


def main():
	"""
	Function Docstring: main()

	This function orchestrates the scraping process by calling the scrape function
	from the avherald_scraper module with specified configuration parameters.
	"""

	# Call the scrape function with specified parameters
	avherald_scraper.scrape(
		# Specify the maximum number of pages to scrape
		max_pages_to_scrape=1,
		# Specify the delay in seconds between requests
		request_delay_seconds=3,
		# Specify whether to show detailed output
		show_details=True
	)


# Check if the script is being run as the main module
if __name__ == "__main__":
	# Call the main function to start the scraping process
	main()
