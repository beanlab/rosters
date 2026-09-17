#!/usr/bin/env python3
"""Convert Markdown to a standalone HTML document with embedded CSS."""

from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
import re

import markdown

TOOLS_DIR = Path(__file__).resolve().parent
DEFAULT_CSS = TOOLS_DIR / "document.css"


def infer_title(source: str, fallback: str) -> str:
    """Use the first Markdown H1 as the document title when available."""
    match = re.search(r"^#\s+(.+?)\s*$", source, flags=re.MULTILINE)
    if not match:
        return fallback
    title = match.group(1)
    title = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", title)
    title = re.sub(r"[*_`~]", "", title)
    return title.strip() or fallback


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert Markdown to standalone, styled HTML."
    )
    parser.add_argument("input", type=Path, help="input Markdown file")
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        help="output HTML file (default: input name with .html suffix)",
    )
    parser.add_argument("--css", type=Path, default=DEFAULT_CSS, help="CSS to embed")
    parser.add_argument("--title", help="HTML document title (default: first H1)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_path = args.input.expanduser().resolve()
    output_path = (
        args.output.expanduser().resolve()
        if args.output
        else source_path.with_suffix(".html")
    )
    css_path = args.css.expanduser().resolve()

    source = source_path.read_text(encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")
    title = args.title or infer_title(source, source_path.stem.replace("-", " ").title())
    body = markdown.markdown(
        source,
        extensions=["extra", "sane_lists"],
        output_format="html5",
    )

    document = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
{css}
  </style>
</head>
<body>
  <main>
{body}
  </main>
</body>
</html>
'''
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
