"""Crawl policy and acquisition-planning helpers."""

from html import unescape
import re
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx


PRIORITY_KEYWORDS = (
    ("pricing", 50),
    ("about", 40),
    ("docs", 30),
    ("security", 20),
    ("product", 10),
)
STRIP_BLOCK_TAGS = ("script", "style", "noscript", "nav", "footer", "header", "svg")


def _registrable_domain(url: str) -> str:
    host = urlsplit(url).netloc.lower().split(":")[0]
    parts = [part for part in host.split(".") if part]
    if len(parts) < 2:
        return host
    return ".".join(parts[-2:])


def should_visit_url(
    seed_url: str,
    candidate_url: str,
    depth: int,
    pages_seen: int,
    robots_allowed: bool,
    max_depth: int = 2,
    max_pages: int = 40,
) -> bool:
    """Return whether a candidate URL should be visited."""
    if not robots_allowed:
        return False
    if depth > max_depth:
        return False
    if pages_seen >= max_pages:
        return False
    return _registrable_domain(seed_url) == _registrable_domain(candidate_url)


def select_fetch_mode(extracted_text: str, minimum_static_chars: int = 20) -> str:
    """Choose between static fetch and JS rendering."""
    if len(extracted_text.strip()) >= minimum_static_chars:
        return "static"
    return "js"


def _normalize_url(url: str) -> str:
    split = urlsplit(url)
    path = split.path or ""
    if path.endswith("/") and path != "/":
        path = path[:-1]
    if path == "/":
        path = ""
    return urlunsplit((split.scheme, split.netloc, path, "", ""))


def _priority_score(url: str) -> int:
    lowered = url.lower()
    score = 0
    for keyword, weight in PRIORITY_KEYWORDS:
        if keyword in lowered:
            score += weight
    return score


def extract_links(base_url: str, html: str) -> list[str]:
    """Extract and rank same-document links from HTML."""
    candidates = re.findall(r"""href=["']([^"']+)["']""", html, flags=re.IGNORECASE)
    normalized: list[str] = []
    for candidate in candidates:
        if candidate.startswith(("mailto:", "tel:", "#", "javascript:")):
            continue
        joined = _normalize_url(urljoin(base_url, candidate))
        normalized.append(joined)
    deduped = list(dict.fromkeys(normalized))
    return sorted(deduped, key=lambda url: (-_priority_score(url), url))


def clean_html_to_text(html: str) -> str:
    """Remove obvious boilerplate blocks and flatten HTML into plain text."""
    cleaned = html
    for tag in STRIP_BLOCK_TAGS:
        cleaned = re.sub(
            rf"<{tag}\b[^>]*>.*?</{tag}>",
            " ",
            cleaned,
            flags=re.IGNORECASE | re.DOTALL,
        )
    cleaned = re.sub(r"<(br|/p|/div|/section|/main|/article|/li|/h[1-6])\b[^>]*>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def strip_external_anchor_text(base_url: str, html: str, seed_url: str) -> str:
    """Remove anchor text for off-domain links before generic HTML cleaning."""

    def _replace(match: re.Match[str]) -> str:
        href = match.group(1)
        text = match.group(2)
        joined = _normalize_url(urljoin(base_url, href))
        if _registrable_domain(joined) != _registrable_domain(seed_url):
            return " "
        return text

    return re.sub(
        r"""<a\b[^>]*href=["']([^"']+)["'][^>]*>(.*?)</a>""",
        _replace,
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )


def fetch_url(url: str, timeout_seconds: float = 10.0) -> str:
    """Fetch a URL using the default static HTTP client."""
    with httpx.Client(follow_redirects=True, timeout=timeout_seconds) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def crawl_priority_pages(
    seed_url: str,
    fetcher: callable | None = None,
    max_pages: int = 4,
    max_depth: int = 1,
    return_failures: bool = False,
) -> list[dict[str, str]] | tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Fetch the seed page and a small set of high-value same-domain pages."""
    fetch = fetcher or fetch_url
    queue: list[tuple[str, int]] = [(_normalize_url(seed_url), 0)]
    seen: set[str] = set()
    collected: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []

    while queue and len(collected) < max_pages:
        current_url, depth = queue.pop(0)
        if current_url in seen:
            continue
        seen.add(current_url)

        try:
            html = fetch(current_url)
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            failures.append({"url": current_url, "error": str(exc)})
            continue
        visible_html = strip_external_anchor_text(current_url, html, seed_url)
        collected.append({"url": current_url, "text": clean_html_to_text(visible_html)})

        if depth >= max_depth:
            continue

        for candidate in extract_links(current_url, html):
            if candidate in seen:
                continue
            if should_visit_url(
                seed_url=seed_url,
                candidate_url=candidate,
                depth=depth + 1,
                pages_seen=len(collected) + len(queue),
                robots_allowed=True,
                max_depth=max_depth,
                max_pages=max_pages,
            ):
                queue.append((candidate, depth + 1))

    if return_failures:
        return collected, failures
    return collected
