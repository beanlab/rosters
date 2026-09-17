"""Command-line interface for locating the installed package."""

from . import path


def main() -> None:
    """Print the absolute path to the installed rosters package."""
    print(path)
