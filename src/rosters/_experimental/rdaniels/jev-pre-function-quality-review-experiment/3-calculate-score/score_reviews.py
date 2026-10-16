#!/usr/bin/env python3
"""Calculate basic and call-depth-weighted scores from Jev judgments."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

import yaml


SCHEMA_VERSION = "1.0"


class ScoringError(ValueError):
    """Raised when the input cannot be scored safely."""


@dataclass(frozen=True)
class Criterion:
    id: str
    category_id: str
    polarity: str


@dataclass
class MetricAccumulator:
    passed: int = 0
    total: int = 0
    weighted_sum: float = 0.0
    total_weight: float = 0.0

    def add(self, passed: int, total: int, score: float | None, weight: float) -> None:
        self.passed += passed
        self.total += total
        if score is not None:
            self.weighted_sum += score * weight
            self.total_weight += weight

    def as_dict(self) -> dict[str, Any]:
        return {
            "basic": {
                "score": _ratio(self.passed, self.total),
                "passed": self.passed,
                "total": self.total,
            },
            "weighted": {
                "score": _ratio(self.weighted_sum, self.total_weight),
                "weighted_sum": _number(self.weighted_sum),
                "total_weight": _number(self.total_weight),
            },
        }


@dataclass
class Aggregate:
    overall: MetricAccumulator = field(default_factory=MetricAccumulator)
    categories: dict[str, MetricAccumulator] = field(
        default_factory=lambda: defaultdict(MetricAccumulator)
    )

    def add_function(self, result: dict[str, Any]) -> None:
        weight = result["weight"]
        basic = result["scores"]["basic"]
        exact_score = basic["passed"] / basic["total"] if basic["total"] else None
        self.overall.add(basic["passed"], basic["total"], exact_score, weight)
        for category_id, category_scores in result["scores"]["categories"].items():
            category_basic = category_scores["basic"]
            category_score = (
                category_basic["passed"] / category_basic["total"]
                if category_basic["total"]
                else None
            )
            self.categories[category_id].add(
                category_basic["passed"],
                category_basic["total"],
                category_score,
                weight,
            )

    def as_dict(self, category_ids: Iterable[str]) -> dict[str, Any]:
        result = self.overall.as_dict()
        result["categories"] = {
            category_id: self.categories[category_id].as_dict()
            for category_id in category_ids
        }
        return result


def _ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def _number(value: float) -> int | float:
    rounded = round(value, 6)
    if rounded.is_integer():
        return int(rounded)
    return rounded


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
    except (OSError, yaml.YAMLError) as error:
        raise ScoringError(f"Could not read judgment YAML {path}: {error}") from error
    if not isinstance(data, dict):
        raise ScoringError("The judgment YAML root must be a mapping.")
    return data


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, json.JSONDecodeError) as error:
        raise ScoringError(f"Could not read function metadata {path}: {error}") from error
    if not isinstance(data, dict):
        raise ScoringError("The function metadata root must be an object.")
    return data


def _criteria(review: dict[str, Any]) -> tuple[list[str], dict[str, Criterion]]:
    checks = review.get("checks")
    groups = checks.get("groups") if isinstance(checks, dict) else None
    if not isinstance(groups, list) or not groups:
        raise ScoringError("The judgment YAML must contain checks.groups.")

    category_ids: list[str] = []
    criteria: dict[str, Criterion] = {}
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("id"), str):
            raise ScoringError("Every check group must have a string id.")
        category_id = group["id"]
        if category_id in category_ids:
            raise ScoringError(f"Duplicate category id: {category_id}")
        category_ids.append(category_id)
        questions = group.get("questions")
        if not isinstance(questions, list):
            raise ScoringError(f"Category {category_id} must contain questions.")
        for question in questions:
            if not isinstance(question, dict):
                raise ScoringError(f"Invalid question in category {category_id}.")
            question_id = question.get("id")
            polarity = question.get("polarity")
            if not isinstance(question_id, str) or polarity not in {"positive", "negative"}:
                raise ScoringError(
                    f"Questions require a string id and positive/negative polarity: {question!r}"
                )
            if question_id in criteria:
                raise ScoringError(f"Duplicate question id: {question_id}")
            criteria[question_id] = Criterion(question_id, category_id, polarity)
    return category_ids, criteria


def _metadata_path(review_path: Path, review: dict[str, Any], override: Path | None) -> Path:
    if override is not None:
        return override
    source = review.get("source")
    raw_path = source.get("input_file") if isinstance(source, dict) else None
    if not isinstance(raw_path, str) or not raw_path:
        raise ScoringError(
            "No source.input_file was provided; pass function metadata with --metadata."
        )
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return review_path.parent / path


def _depths(metadata: dict[str, Any]) -> dict[str, int]:
    functions = metadata.get("functions")
    if not isinstance(functions, list):
        raise ScoringError("Function metadata must contain a functions list.")
    depths: dict[str, int] = {}
    for function in functions:
        if not isinstance(function, dict) or not isinstance(function.get("id"), str):
            raise ScoringError("Every metadata function must have a string id.")
        depth = function.get("depth_to_leaf")
        if not isinstance(depth, int) or isinstance(depth, bool) or depth < 0:
            raise ScoringError(
                f"Function {function['id']} has an invalid depth_to_leaf: {depth!r}"
            )
        depths[function["id"]] = depth
    return depths


def _module_for(file_name: str) -> str:
    normalized = file_name.replace("\\", "/")
    parent = str(PurePosixPath(normalized).parent)
    return parent if parent not in {"", "/"} else "."


def _probability(response: dict[str, Any], polarity: str, question_id: str) -> tuple[str, float]:
    answer = "yes" if polarity == "positive" else "no"
    key = f"probability_{answer}"
    value = response.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ScoringError(f"Response {question_id} requires a finite numeric {key}.")
    probability = float(value)
    if not 0.0 <= probability <= 1.0:
        raise ScoringError(f"Response {question_id} has {key} outside [0, 1].")
    return answer, probability


def _score_function(
    function: dict[str, Any],
    criteria: dict[str, Criterion],
    category_ids: list[str],
    depth: int,
    threshold: float,
) -> dict[str, Any]:
    function_id = function.get("id")
    file_name = function.get("file")
    responses = function.get("responses")
    if not isinstance(function_id, str) or not isinstance(file_name, str):
        raise ScoringError("Every judged function must have string id and file values.")
    if not isinstance(responses, dict):
        raise ScoringError(f"Function {function_id} must contain responses.")

    unknown = sorted(set(responses) - set(criteria))
    missing = sorted(set(criteria) - set(responses))
    if unknown or missing:
        details = []
        if unknown:
            details.append(f"unknown responses: {', '.join(unknown)}")
        if missing:
            details.append(f"missing responses: {', '.join(missing)}")
        raise ScoringError(f"Function {function_id} has " + "; ".join(details))

    question_results: dict[str, Any] = {}
    category_counts = {category_id: [0, 0] for category_id in category_ids}
    passed_count = 0
    for question_id, criterion in criteria.items():
        response = responses[question_id]
        if not isinstance(response, dict):
            raise ScoringError(f"Response {question_id} in {function_id} must be a mapping.")
        answer, probability = _probability(response, criterion.polarity, question_id)
        passed = probability >= threshold
        passed_count += int(passed)
        category_counts[criterion.category_id][0] += int(passed)
        category_counts[criterion.category_id][1] += 1
        question_results[question_id] = {
            "category": criterion.category_id,
            "polarity": criterion.polarity,
            "favorable_answer": answer,
            "favorable_probability": round(probability, 6),
            "passed": passed,
        }

    total = len(criteria)
    weight = depth + 1
    basic_score = _ratio(passed_count, total)
    categories = {}
    for category_id in category_ids:
        category_passed, category_total = category_counts[category_id]
        score = _ratio(category_passed, category_total)
        categories[category_id] = {
            "basic": {"score": score, "passed": category_passed, "total": category_total},
            "weighted": {
                "score": score,
                "weighted_contribution": round((score or 0.0) * weight, 6),
                "weight": weight,
            },
        }

    return {
        "id": function_id,
        "file": file_name,
        "module": _module_for(file_name),
        "name": function.get("name"),
        "qualified_name": function.get("qualified_name"),
        "line": function.get("line"),
        "depth_to_leaf": depth,
        "weight": weight,
        "scores": {
            "basic": {"score": basic_score, "passed": passed_count, "total": total},
            "weighted": {
                "score": basic_score,
                "weighted_contribution": round((basic_score or 0.0) * weight, 6),
                "weight": weight,
            },
            "categories": categories,
        },
        "criteria": question_results,
    }


def calculate_scores(
    review_path: Path, threshold: float = 0.85, metadata_path: Path | None = None
) -> dict[str, Any]:
    """Load one review and return its complete score document."""
    if not math.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise ScoringError("Threshold must be a finite number between 0 and 1.")

    review_path = review_path.resolve()
    review = _load_yaml(review_path)
    category_ids, criteria = _criteria(review)
    resolved_metadata_path = _metadata_path(review_path, review, metadata_path)
    resolved_metadata_path = resolved_metadata_path.resolve()
    depths = _depths(_load_json(resolved_metadata_path))

    raw_functions = review.get("functions")
    if not isinstance(raw_functions, list) or not raw_functions:
        raise ScoringError("The judgment YAML must contain a non-empty functions list.")

    function_results = []
    seen_ids: set[str] = set()
    for function in raw_functions:
        if not isinstance(function, dict) or not isinstance(function.get("id"), str):
            raise ScoringError("Every judged function must be a mapping with a string id.")
        function_id = function["id"]
        if function_id in seen_ids:
            raise ScoringError(f"Duplicate judged function id: {function_id}")
        seen_ids.add(function_id)
        if function_id not in depths:
            raise ScoringError(f"No depth metadata found for judged function {function_id}.")
        function_results.append(
            _score_function(function, criteria, category_ids, depths[function_id], threshold)
        )

    overall = Aggregate()
    files: dict[str, Aggregate] = defaultdict(Aggregate)
    modules: dict[str, Aggregate] = defaultdict(Aggregate)
    file_function_ids: dict[str, list[str]] = defaultdict(list)
    module_file_ids: dict[str, set[str]] = defaultdict(set)
    for result in function_results:
        overall.add_function(result)
        files[result["file"]].add_function(result)
        modules[result["module"]].add_function(result)
        file_function_ids[result["file"]].append(result["id"])
        module_file_ids[result["module"]].add(result["file"])

    return {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "judgments_file": str(review_path),
            "function_metadata_file": str(resolved_metadata_path),
            "judgment_schema_version": review.get("schema_version"),
        },
        "scoring": {
            "threshold": threshold,
            "threshold_comparison": "favorable_probability >= threshold",
            "basic_score": "passed criteria / evaluated criteria",
            "favorable_probability": {
                "positive_criterion": "probability_yes",
                "negative_criterion": "probability_no",
            },
            "function_weight": "depth_to_leaf + 1",
            "weighted_aggregate": "sum(function basic score * function weight) / sum(function weight)",
            "module_definition": "parent directory of the reviewed file; '.' means repository root",
        },
        "overall": overall.as_dict(category_ids),
        "modules": [
            {
                "id": module_id,
                "files": sorted(module_file_ids[module_id]),
                "scores": modules[module_id].as_dict(category_ids),
            }
            for module_id in sorted(modules)
        ],
        "files": [
            {
                "id": file_id,
                "module": _module_for(file_id),
                "functions": file_function_ids[file_id],
                "scores": files[file_id].as_dict(category_ids),
            }
            for file_id in sorted(files)
        ],
        "functions": function_results,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Calculate basic and call-depth-weighted scores from Jev judgment YAML."
    )
    parser.add_argument("input", type=Path, help="Path to function-review.yaml")
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("scores.yaml"), help="Output YAML path"
    )
    parser.add_argument(
        "--threshold", type=float, default=0.85, help="Passing probability (default: 0.85)"
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        help="Override the function metadata JSON path from source.input_file",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = calculate_scores(args.input, args.threshold, args.metadata)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="\n") as stream:
            yaml.safe_dump(result, stream, sort_keys=False, allow_unicode=True)
    except (OSError, ScoringError) as error:
        raise SystemExit(f"error: {error}") from error
    print(f"Wrote scores to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
