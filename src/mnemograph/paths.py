"""Filesystem layout helpers for Mnemograph."""

from pathlib import Path


def mirror_paths(base_dir: str | Path) -> dict[str, str]:
    """Return the public memory mirror layout."""
    root = Path(base_dir)
    return {
        "working": str(root / "working"),
        "knowledge": str(root / "knowledge"),
        "sources": str(root / "sources"),
    }
