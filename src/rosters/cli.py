"""Command-line interface for locating the installed package."""

from pathlib import Path


def main() -> None:
    """Print the absolute path to the installed rosters package."""
    print(Path(__file__).resolve().parent)
