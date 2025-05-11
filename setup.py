from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

# load long description from README.md if exists
long_description = (
	'The Aviation Herald Scraper is a Python tool designed to automatically extract basic incident information from the front page headlines of avherald.com and '
	'stores them in a local SQLite database.'
)

readme = here / "README.md"
if readme.exists():
	long_description = readme.read_text(encoding="utf-8")

setup(
	name="avherald-scraper",
	version="1.0.2",
	description="Scrapes aviation incident data from AV Herald website",
	long_description=long_description,
	long_description_content_type="text/markdown",
	author="Kolja Nolte",
	author_email="kolja.nolte@gmail.com",
	url="https://www.kolja-nolte.com",
	packages=find_packages(include=["avherald_scraper", "avherald_scraper.*"]),
	python_requires=">=3.7",
	install_requires=[
		"requests",
		"beautifulsoup4",
		"lxml"
	],
	entry_points={
		"console_scripts": [
			"avherald-scraper=main:main"
		]
	},
	classifiers=[
		"License :: OSI Approved :: MIT License",
		"Programming Language :: Python :: 3",
		"Programming Language :: Python :: 3.7",
		"Topic :: Software Development :: Web Scraping"
	]
)
