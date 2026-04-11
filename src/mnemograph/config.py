"""Project-level configuration helpers."""

from pathlib import Path


def package_root() -> Path:
    """Return the package root for the Mnemograph project."""
    return Path(__file__).resolve().parents[2]
