from avherald_scraper.urls import (
    canonical_article_url,
    list_page_url,
    parse_article_href,
)


def test_parses_absolute_article_url_and_drops_opt():
    ref = parse_article_href("https://avherald.com/h?article=53f3f5aa&opt=0")
    assert ref is not None
    assert ref.article_id == "53f3f5aa"
    assert ref.url == "https://avherald.com/h?article=53f3f5aa"


def test_parses_relative_article_href():
    ref = parse_article_href("/h?article=53ef846a&opt=0")
    assert ref is not None
    assert ref.article_id == "53ef846a"
    assert ref.url == "https://avherald.com/h?article=53ef846a"


def test_folds_uppercase_hex_to_lowercase():
    ref = parse_article_href("/h?article=53F6903D&opt=0")
    assert ref is not None
    assert ref.article_id == "53f6903d"


def test_rejects_login_and_list_urls():
    assert parse_article_href("/h?login=&opt=0") is None
    assert parse_article_href("/h?list=&opt=0") is None
    assert parse_article_href("/h?subscribe=&opt=0") is None


def test_rejects_article_id_that_is_not_eight_hex_chars():
    assert parse_article_href("/h?article=53f3f5aaXX") is None
    assert parse_article_href("/h?article=53f3f5a") is None
    assert parse_article_href("/h?article=zzzzzzzz") is None


def test_canonical_article_url():
    assert canonical_article_url("53f3f5aa") == "https://avherald.com/h?article=53f3f5aa"


def test_default_list_url_is_the_homepage():
    assert list_page_url("https://avherald.com") == "https://avherald.com/"


def test_list_url_sort_by_occurrence():
    assert list_page_url("https://avherald.com", sort="occurrence") == (
        "https://avherald.com/h?list=&opt=1"
    )


def test_list_url_category_bits_combine_with_sort():
    url = list_page_url(
        "https://avherald.com",
        sort="occurrence",
        categories=("incident", "accident"),
    )
    assert url == "https://avherald.com/h?list=&opt=1537"
