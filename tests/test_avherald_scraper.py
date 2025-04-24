import avherald_scraper.avherald_scraper as avherald_scraper


# Defines the test case for the date_to_timestamp function with valid input.
def test_date_to_timestamp_valid():
	# Asserts that the date "Mar 31st 2025" is correctly converted to its timestamp.
	assert avherald_scraper.date_to_timestamp("Mar 31st 2025") == 1743379200
	# Asserts that the date "Jan 1st 2020" is correctly converted to its timestamp.
	assert avherald_scraper.date_to_timestamp("Jan 1st 2020") == 1577836800


# Defines the test case for the date_to_timestamp function with invalid input.
def test_date_to_timestamp_invalid():
	# Asserts that an empty string input to date_to_timestamp returns None.
	assert avherald_scraper.date_to_timestamp("") is None
	# Asserts that an invalid date string input to date_to_timestamp returns None.
	assert avherald_scraper.date_to_timestamp("Not a date") is None


# Defines a test case for process_title when all fields are present.
def test_process_title_with_all_fields():
	# Defines a title string with all fields present.
	title = "Boeing 737 at Berlin on Mar 31st 2025, engine failure"
	# Processes the title string using the process_title function.
	result = avherald_scraper.process_title(title)
	# Asserts that the cleaned title is extracted correctly.
	assert result['cleaned_title'] == "Boeing 737 at Berlin"
	# Asserts that the cause is extracted correctly.
	assert result['cause'] == "Engine failure"
	# Asserts that the location is extracted correctly.
	assert result['location'] == "Berlin"
	# Asserts that the timestamp is extracted and converted correctly.
	assert result['timestamp'] == 1743379200


# Defines a test case for process_title when the location is missing.
def test_process_title_without_location():
	# Defines a title string without location.
	title = "Airbus A320 on Mar 31st 2025, bird strike"
	# Processes the title string using the process_title function.
	result = avherald_scraper.process_title(title)
	# Asserts that the location is set to "Unknown" when it's missing from the title.
	assert result['location'] == "Unknown"
	# Asserts that the cause is extracted correctly.
	assert result['cause'] == "Bird strike"


# Defines a test case for process_title when the cause is missing.
def test_process_title_without_cause():
	# Defines a title string without cause.
	title = "Cessna 172 at Paris on Jan 1st 2020"
	# Processes the title string using the process_title function.
	result = avherald_scraper.process_title(title)
	# Asserts that the cause is set to "Not specified" when it's missing from the title.
	assert result['cause'] == "Not specified"
	# Asserts that the location is extracted correctly.
	assert result['location'] == "Paris"


# Defines a test case for process_title when the date is missing.
def test_process_title_without_date():
	# Defines a title string without date.
	title = "Piper PA-28 at London, gear up landing"
	# Processes the title string using the process_title function.
	result = avherald_scraper.process_title(title)
	# Asserts that the timestamp is None when the date is missing.
	assert result['timestamp'] is None
	# Asserts that the location is extracted correctly.
	assert result['location'] == "London"
	# Asserts that the cause is extracted correctly.
	assert result['cause'] == "Gear up landing"


# Defines a test case for process_title with minimal information.
def test_process_title_minimal():
	# Defines a minimal title string.
	title = "Unknown incident"
	# Processes the title string using the process_title function.
	result = avherald_scraper.process_title(title)
	# Asserts that the cause is set to "Not specified" when the title is minimal.
	assert result['cause'] == "Not specified"
	# Asserts that the location is set to "Unknown" when the title is minimal.
	assert result['location'] == "Unknown"
	# Asserts that the timestamp is None when the title is minimal.
	assert result['timestamp'] is None


# Defines a test case for insert_incident and insert_incidents functions.
def test_insert_incident_and_insert_incidents(tmp_path):
	# Creates a temporary database file path using tmp_path fixture.
	db_file = tmp_path / "test.sqlite"
	# Connects to the SQLite database.
	conn = avherald_scraper.sqlite3.connect(str(db_file))
	# Creates the incident table if it doesn't exist.
	avherald_scraper.create_table_if_not_exists(conn)
	# Defines a sample incident dictionary.
	incident = {
		# Defines the category of the incident.
		'category':  'incident',
		# Defines the title of the incident.
		'title':     'Test Title',
		# Defines the location of the incident.
		'location':  'Test Location',
		# Defines the cause of the incident.
		'cause':     'Test Cause',
		# Defines the timestamp of the incident.
		'timestamp': 1234567890,
		# Defines the URL of the incident.
		'url':       'http://example.com'
	}
	# Asserts that the first insertion of the incident is successful (returns True).
	assert avherald_scraper.insert_incident(conn, incident) is True
	# Asserts that a duplicate insertion of the incident is skipped (returns False).
	assert avherald_scraper.insert_incident(conn, incident) is False
	# Defines a list of incidents to be inserted.
	incidents = [incident, dict(incident, title='Test Title 2')]
	# Inserts the list of incidents into the database.
	inserted, skipped = avherald_scraper.insert_incidents(conn, incidents)
	# Asserts that one incident was inserted.
	assert inserted == 1
	# Asserts that one incident was skipped.
	assert skipped == 1
	# Closes the database connection.
	conn.close()


# Defines a test case for scrape_single_page function.
def test_scrape_single_page(monkeypatch):
	# Defines a mock HTML content for testing.
	html = """
    <html>
    <body>
        <table>
            <tr>
                <td><img src="incident.gif"></td>
                <td>
                    <a href="/article1">
                        <span class="headline_avherald">Boeing 737 at Berlin on Mar 31st 2025, engine failure</span>
                    </a>
                </td>
            </tr>
        </table>
        <a href="/nextpage"><img src="next.jpg"></a>
    </body>
    </html>
    """

	# Defines a mock response class for simulating HTTP responses.
	class MockResponse:
		# Initializes the MockResponse object with text, status code, and encoding.
		def __init__(self, text):
			# Sets the text of the response.
			self.text = text
			# Sets the status code of the response.
			self.status_code = 200
			# Sets the encoding of the response.
			self.encoding = 'utf-8'

		# Defines a mock method to simulate raising an exception for bad status codes.
		def raise_for_status(self): pass

	# Defines a mock function for simulating HTTP GET requests.
	def mock_get(*args, **kwargs):
		# Returns a MockResponse object with the defined HTML content.
		return MockResponse(html)

	# Uses monkeypatch to replace the requests.get function with the mock_get function.
	monkeypatch.setattr(avherald_scraper.requests, "get", mock_get)
	# Scrapes a single page using the mock HTTP response.
	incidents, next_url = avherald_scraper.scrape_single_page("http://fakeurl", show_details=False)
	# Asserts that the number of incidents scraped is 1.
	assert len(incidents) == 1
	# Asserts that the title of the scraped incident is correct.
	assert incidents[0]['title'] == "Boeing 737 at Berlin"
	# Asserts that the next URL extracted is correct.
	assert next_url.endswith("/nextpage")
