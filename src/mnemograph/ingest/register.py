"""Source registration helpers."""

from dataclasses import dataclass
import hashlib
from urllib.parse import urlsplit, urlunsplit


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    source_type: str
    locator: str
    normalized_locator: str
    content_hash: str


def compute_content_hash(content: str) -> str:
    """Return a stable SHA-256 hash for source content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def normalize_locator(source_type: str, locator: str) -> str:
    """Normalize a locator for stable source identity."""
    if source_type != "url":
        return locator.strip()

    parts = urlsplit(locator.strip())
    normalized_path = parts.path.rstrip("/") or "/"
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            "" if normalized_path == "/" else normalized_path,
            parts.query,
            "",
        )
    )


def register_source(source_type: str, locator: str, content: str) -> SourceRecord:
    """Create a deterministic source-registration record."""
    normalized_locator = normalize_locator(source_type, locator)
    content_hash = compute_content_hash(content)
    source_id = compute_content_hash(f"{source_type}:{normalized_locator}:{content_hash}")
    return SourceRecord(
        source_id=source_id,
        source_type=source_type,
        locator=locator,
        normalized_locator=normalized_locator,
        content_hash=content_hash,
    )
