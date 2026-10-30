import httpx

from avherald_scraper.http import BlockedError, Client


def test_get_returns_body_and_does_not_sleep_on_first_request(list_page_html: str):
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=list_page_html)

    client = Client(
        delay=3,
        transport=httpx.MockTransport(handler),
        sleeper=sleeps.append,
    )
    body = client.get("https://avherald.com/")
    assert "headline_avherald" in body
    assert sleeps == []


def test_get_sleeps_before_second_request(list_page_html: str):
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=list_page_html)

    client = Client(
        delay=3,
        transport=httpx.MockTransport(handler),
        sleeper=sleeps.append,
    )
    client.get("https://avherald.com/")
    client.get("https://avherald.com/h?list=&opt=0")
    assert sleeps == [3]


def test_blocked_proxy_rotates_to_the_next_host(list_page_html: str, blocked_page_html: str):
    client = Client(
        delay=0,
        proxies=("http://proxy-a:8080", "http://proxy-b:8080"),
        sleeper=lambda _seconds: None,
    )
    script = [blocked_page_html, list_page_html]
    used: list[str | None] = []

    class FakeResponse:
        def __init__(self, text: str):
            self.text = text

        def raise_for_status(self) -> None:
            return None

    class FakeHttp:
        def __init__(self, proxy: str | None):
            self.proxy = proxy

        def get(self, url: str) -> FakeResponse:
            used.append(self.proxy)
            return FakeResponse(script.pop(0))

        def close(self) -> None:
            return None

    def open_fake() -> None:
        client._http = FakeHttp(client._current_proxy())

    client._http.close()
    client._open = open_fake
    open_fake()
    body = client.get("https://avherald.com/")
    assert "headline_avherald" in body
    assert used == ["http://proxy-a:8080", "http://proxy-b:8080"]
    client.close()


def test_get_raises_blocked_error(blocked_page_html: str):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=blocked_page_html)

    client = Client(delay=0, transport=httpx.MockTransport(handler), sleeper=lambda _: None)
    try:
        client.get("https://avherald.com/")
    except BlockedError as exc:
        assert "unauthorized accesses" in str(exc).lower() or "blocked" in str(exc).lower()
    else:
        raise AssertionError("expected BlockedError")
