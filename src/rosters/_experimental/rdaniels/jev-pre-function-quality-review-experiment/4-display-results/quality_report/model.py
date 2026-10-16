"""Validation and normalization for score report inputs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ScoreFileError(ValueError):
    """Raised when a score file cannot be represented by the report."""


@dataclass(frozen=True)
class ScoreInput:
    path: Path
    name: str | None = None


def load_project(score_input: ScoreInput) -> dict[str, Any]:
    path = score_input.path
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ScoreFileError(f"Could not read {path}: {error}") from error
    except yaml.YAMLError as error:
        raise ScoreFileError(f"Invalid YAML in {path}: {error}") from error

    if not isinstance(raw, dict):
        raise ScoreFileError(f"{path} must contain a YAML mapping")

    required = ("overall", "files", "functions")
    missing = [key for key in required if key not in raw]
    if missing:
        raise ScoreFileError(f"{path} is missing required keys: {', '.join(missing)}")

    overall = _score_container(raw["overall"], path, "overall")
    files = [_entity(item, path, "file") for item in _list(raw["files"], path, "files")]
    metadata = _load_metadata(raw, path)
    function_metadata = _function_metadata(metadata)
    functions = [
        _function(item, path, function_metadata)
        for item in _list(raw["functions"], path, "functions")
    ]
    modules = [
        _entity(item, path, "module")
        for item in _list(raw.get("modules", []), path, "modules")
    ]

    categories = _ordered_categories(overall, files, functions)
    criteria = _criterion_catalog(functions)
    name = score_input.name or _default_name(path)

    return {
        "name": name,
        "sourceFile": str(path),
        "capturedAt": _captured_at(metadata),
        "schemaVersion": str(raw.get("schema_version", "unknown")),
        "threshold": raw.get("scoring", {}).get("threshold"),
        "overall": overall,
        "categories": categories,
        "criteria": criteria,
        "modules": modules,
        "files": files,
        "functions": functions,
    }


def _default_name(path: Path) -> str:
    return path.parent.name if path.stem.lower() == "scores" else path.stem


def _list(value: Any, path: Path, key: str) -> list[Any]:
    if not isinstance(value, list):
        raise ScoreFileError(f"{path}: {key} must be a list")
    return value


def _entity(value: Any, path: Path, kind: str) -> dict[str, Any]:
    if not isinstance(value, dict) or "id" not in value or "scores" not in value:
        raise ScoreFileError(f"{path}: each {kind} needs id and scores")
    entity = dict(value)
    entity["scores"] = _score_container(value["scores"], path, f"{kind} {value['id']}")
    return entity


def _function(
    value: Any,
    path: Path,
    function_metadata: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    entity = _entity(value, path, "function")
    criteria = value.get("criteria", {})
    if not isinstance(criteria, dict):
        raise ScoreFileError(f"{path}: function {value['id']} criteria must be a mapping")
    entity["criteria"] = criteria
    metadata = function_metadata.get(str(value["id"]), {})
    for key in ("source", "signature", "end_line"):
        if key in metadata:
            entity[key] = metadata[key]
    return entity


def _load_metadata(raw: dict[str, Any], score_path: Path) -> dict[str, Any]:
    source = raw.get("source", {})
    metadata_file = source.get("function_metadata_file") if isinstance(source, dict) else None
    if not isinstance(metadata_file, str) or not metadata_file:
        return {}

    metadata_path = Path(metadata_file)
    if not metadata_path.is_absolute():
        metadata_path = score_path.parent / metadata_path
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return metadata if isinstance(metadata, dict) else {}


def _function_metadata(metadata: dict[str, Any]) -> dict[str, dict[str, Any]]:
    functions = metadata.get("functions", []) if isinstance(metadata, dict) else []
    return {
        str(item["id"]): item
        for item in functions
        if isinstance(item, dict) and "id" in item
    }


def _captured_at(metadata: dict[str, Any]) -> str | None:
    git = metadata.get("git")
    cutoff = git.get("cutoff") if isinstance(git, dict) else None
    return cutoff if isinstance(cutoff, str) else None


def _score_container(value: Any, path: Path, context: str) -> dict[str, Any]:
    if not isinstance(value, dict) or "basic" not in value:
        raise ScoreFileError(f"{path}: {context} needs a basic score")
    basic = value["basic"]
    if not isinstance(basic, dict) or not isinstance(basic.get("score"), (int, float)):
        raise ScoreFileError(f"{path}: {context} basic score must be numeric")
    return value


def _ordered_categories(
    overall: dict[str, Any],
    files: list[dict[str, Any]],
    functions: list[dict[str, Any]],
) -> list[str]:
    seen: dict[str, None] = {}
    for container in [overall, *files, *functions]:
        categories = container.get("categories", {})
        if isinstance(categories, dict):
            for category in categories:
                seen.setdefault(category, None)
    return list(seen)


def _criterion_catalog(functions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for function in functions:
        for criterion, result in function["criteria"].items():
            if criterion not in catalog and isinstance(result, dict):
                catalog[criterion] = {
                    "category": result.get("category"),
                    "polarity": result.get("polarity"),
                    "favorableAnswer": result.get("favorable_answer"),
                }
    return catalog
