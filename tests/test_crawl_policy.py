import httpx

from mnemograph.ingest.crawl import crawl_priority_pages, select_fetch_mode, should_visit_url


def test_should_visit_url_enforces_same_domain():
    assert should_visit_url(
        seed_url="https://acme.com",
        candidate_url="https://docs.acme.com/pricing",
        depth=1,
        pages_seen=1,
        robots_allowed=True,
    )
    assert not should_visit_url(
        seed_url="https://acme.com",
        candidate_url="https://other.com/pricing",
        depth=1,
        pages_seen=1,
        robots_allowed=True,
    )


def test_should_visit_url_enforces_depth_limit():
    assert should_visit_url(
        seed_url="https://acme.com",
        candidate_url="https://acme.com/pricing",
        depth=2,
        pages_seen=1,
        robots_allowed=True,
    )
    assert not should_visit_url(
        seed_url="https://acme.com",
        candidate_url="https://acme.com/pricing",
        depth=3,
        pages_seen=1,
        robots_allowed=True,
    )


def test_should_visit_url_enforces_page_count_limit():
    assert should_visit_url(
        seed_url="https://acme.com",
        candidate_url="https://acme.com/pricing",
        depth=1,
        pages_seen=39,
        robots_allowed=True,
    )
    assert not should_visit_url(
        seed_url="https://acme.com",
        candidate_url="https://acme.com/pricing",
        depth=1,
        pages_seen=40,
        robots_allowed=True,
    )


def test_should_visit_url_respects_robots():
    assert not should_visit_url(
        seed_url="https://acme.com",
        candidate_url="https://acme.com/private",
        depth=1,
        pages_seen=1,
        robots_allowed=False,
    )


def test_select_fetch_mode_prefers_js_render_only_for_content_poor_pages():
    assert select_fetch_mode(extracted_text="pricing plans and product overview") == "static"
    assert select_fetch_mode(extracted_text="Buy now") == "js"


def test_crawl_priority_pages_continues_when_one_page_fails():
    pages = {
        "https://acme.com": '<html><body><main><a href="/pricing">Pricing</a><a href="/about">About</a></main></body></html>',
        "https://acme.com/about": '<html><body><main><p>About Acme.</p></main></body></html>',
    }

    def fetcher(url: str) -> str:
        if url.endswith("/pricing"):
            raise httpx.HTTPError("boom")
        return pages[url]

    results = crawl_priority_pages("https://acme.com", fetcher=fetcher, max_pages=3)

    assert [page["url"] for page in results] == ["https://acme.com", "https://acme.com/about"]
