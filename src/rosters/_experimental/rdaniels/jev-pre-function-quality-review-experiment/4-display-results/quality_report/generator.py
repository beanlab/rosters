"""Render normalized score projects into a self-contained HTML document."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Iterable

from .model import ScoreInput, load_project


def build_report(
    inputs: Iterable[ScoreInput],
    output: Path,
    title: str = "Code quality atlas",
) -> None:
    projects = [load_project(item) for item in inputs]
    if not projects:
        raise ValueError("At least one score file is required")

    payload = json.dumps(
        {"title": title, "projects": projects},
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("<", "\\u003c")
    template = files("quality_report").joinpath("report.html").read_text(encoding="utf-8")
    html = template.replace("{{REPORT_TITLE}}", _escape_html(title)).replace(
        "{{REPORT_DATA}}", payload
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")


def _escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
