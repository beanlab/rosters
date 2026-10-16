#!/usr/bin/env python3
"""Evaluate parsed functions with Jev Noul questions."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR.parent / "results" / "1-parse-repo" / "parsed.json"
DEFAULT_OUTPUT = SCRIPT_DIR.parent / "results" / "2-set-up-and-call-jev" / "function-review.yaml"
DEFAULT_CHECKS = SCRIPT_DIR / "code-checks.yaml"
DEFAULT_MODEL = "jev-latest"
DEFAULT_PRICE_PER_MILLION_INPUT_TOKENS = 0.042
DEFAULT_FIXED_TOKENS_PER_REQUEST = 200


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Review each parsed function with editable Jev Noul checks."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--checks", type=Path, default=DEFAULT_CHECKS)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--price-per-million-input-tokens",
        type=float,
        default=DEFAULT_PRICE_PER_MILLION_INPUT_TOKENS,
    )
    parser.add_argument(
        "--fixed-tokens-per-request",
        type=int,
        default=DEFAULT_FIXED_TOKENS_PER_REQUEST,
        help="Conservative per-request overhead used only by the preflight estimate.",
    )
    parser.add_argument(
        "--estimate-only",
        action="store_true",
        help="Print the cost estimate and exit without calling Jev.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Approve the displayed estimate non-interactively.",
    )
    return parser.parse_args(argv)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as input_file:
        value = json.load(input_file)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def load_checks(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with path.open(encoding="utf-8") as checks_file:
        config = yaml.safe_load(checks_file)
    if not isinstance(config, dict) or not isinstance(config.get("groups"), list):
        raise ValueError(f"Expected {path} to contain a top-level groups list")

    flattened: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for group in config["groups"]:
        if not isinstance(group, dict) or not isinstance(group.get("questions"), list):
            raise ValueError("Each check group must contain a questions list")
        for question in group["questions"]:
            if not isinstance(question, dict):
                raise ValueError("Each question must be a mapping")
            question_id = question.get("id")
            polarity = question.get("polarity")
            criteria = question.get("criteria")
            if not isinstance(question_id, str) or not question_id:
                raise ValueError("Every question must have a non-empty id")
            if question_id in seen_ids:
                raise ValueError(f"Duplicate question id: {question_id}")
            if polarity not in {"positive", "negative"}:
                raise ValueError(f"Question {question_id} has invalid polarity")
            if not isinstance(question.get("instructions"), str):
                raise ValueError(f"Question {question_id} must have string instructions")
            if not isinstance(criteria, dict) or not all(
                isinstance(criteria.get(key), str) for key in ("true", "false")
            ):
                raise ValueError(f"Question {question_id} needs true/false criteria")
            seen_ids.add(question_id)
            flattened.append(question)
    if not flattened:
        raise ValueError("At least one question is required")
    return config, flattened


def validate_input(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    functions = data.get("functions")
    if not isinstance(functions, list):
        raise ValueError("Input JSON must contain a functions list")
    required = {"id", "file", "name", "signature", "source"}
    for index, function in enumerate(functions):
        if not isinstance(function, dict) or not required.issubset(function):
            missing = required - set(function) if isinstance(function, dict) else required
            raise ValueError(f"Function {index} is invalid; missing: {sorted(missing)}")
    return functions


def build_states(functions: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_class: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for function in functions:
        by_file[function["file"]].append(function)
        owner_class = function.get("owner_class")
        if owner_class:
            by_class[(function["file"], owner_class)].append(function)

    states: list[dict[str, Any]] = []
    for target in functions:
        other_file_functions = [
            {
                "id": related["id"],
                "signature": related["signature"],
                "source": related["source"],
            }
            for related in by_file[target["file"]]
            if related["id"] != target["id"]
        ]
        owner_class = target.get("owner_class")
        class_functions = by_class.get((target["file"], owner_class), []) if owner_class else []
        states.append(
            {
                "task": (
                    "Judge only target_function. Use related_context only where a question "
                    "explicitly asks about file or class context."
                ),
                "target_function": target,
                "related_context": {
                    "other_file_function_count": len(other_file_functions),
                    "other_file_functions": other_file_functions,
                    "owner_class": owner_class,
                    "owner_class_function_count": len(class_functions),
                    "owner_class_function_signatures": [
                        function["signature"] for function in class_functions
                    ],
                },
            }
        )
    return states


def question_payload(checks: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        check["id"]: {
            "type": "noul",
            "instructions": check["instructions"],
            "criteria": check["criteria"],
        }
        for check in checks
    }


def estimate_tokens(value: Any) -> int:
    serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return math.ceil(len(serialized.encode("utf-8")) / 4)


def estimate_run(
    states: Sequence[dict[str, Any]],
    questions: Mapping[str, Any],
    fixed_tokens_per_request: int,
    price_per_million: float,
) -> dict[str, Any]:
    if fixed_tokens_per_request < 0:
        raise ValueError("fixed tokens per request cannot be negative")
    if price_per_million < 0:
        raise ValueError("price cannot be negative")
    question_tokens = estimate_tokens(questions)
    request_tokens = [
        estimate_tokens(state) + question_tokens + fixed_tokens_per_request
        for state in states
    ]
    total_tokens = sum(request_tokens)
    return {
        "method": "UTF-8 bytes / 4 plus fixed per-request overhead",
        "request_count": len(states),
        "question_count_per_request": len(questions),
        "fixed_tokens_per_request": fixed_tokens_per_request,
        "estimated_input_tokens": total_tokens,
        "price_per_million_input_tokens_usd": price_per_million,
        "estimated_cost_usd": total_tokens * price_per_million / 1_000_000,
    }


def display_estimate(estimate: Mapping[str, Any]) -> None:
    print("Jev preflight estimate (no Jev calls made)")
    print(f"  Requests: {estimate['request_count']}")
    print(f"  Questions per request: {estimate['question_count_per_request']}")
    print(f"  Estimated input tokens: {estimate['estimated_input_tokens']:,}")
    print(
        "  Assumed price: "
        f"${estimate['price_per_million_input_tokens_usd']:.6f} per 1M input tokens"
    )
    print(f"  Estimated cost: ${estimate['estimated_cost_usd']:.8f}")
    print(f"  Heuristic: {estimate['method']}")


def get_approval(approved_by_flag: bool) -> bool:
    if approved_by_flag:
        print("Cost approved via --yes.")
        return True
    if not sys.stdin.isatty():
        print("Refusing to call Jev without interactive approval or --yes.", file=sys.stderr)
        return False
    answer = input("Proceed with Jev calls? [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def build_noul_questions(checks: Sequence[dict[str, Any]]) -> dict[str, Any]:
    from typesafe_sdk import Noul, NoulCriteria

    return {
        check["id"]: Noul(
            instructions=check["instructions"],
            criteria=NoulCriteria(
                true=check["criteria"]["true"],
                false=check["criteria"]["false"],
            ),
        )
        for check in checks
    }


def run_reviews(
    states: Sequence[dict[str, Any]],
    functions: Sequence[dict[str, Any]],
    checks: Sequence[dict[str, Any]],
    model: str,
) -> tuple[list[dict[str, Any]], dict[str, int], list[str]]:
    from typesafe_sdk import TypeSafeClient

    questions = build_noul_questions(checks)
    results: list[dict[str, Any]] = []
    total_usage = {"input_tokens": 0, "output_tokens": 0}
    resolved_models: set[str] = set()

    with TypeSafeClient(model=model) as client:
        for index, (function, state) in enumerate(zip(functions, states), start=1):
            print(f"[{index}/{len(functions)}] Reviewing {function['id']}")
            response = client.system_one(state=state, questions=questions)
            resolved_models.add(response.model)
            usage = response.usage.model_dump()
            total_usage["input_tokens"] += usage["input_tokens"]
            total_usage["output_tokens"] += usage["output_tokens"]
            responses = {
                check["id"]: {
                    "type": "noul",
                    "polarity": check["polarity"],
                    "yes_means": "good" if check["polarity"] == "positive" else "bad",
                    "probability_yes": response.answers[check["id"]].noul,
                    "probability_no": 1.0 - response.answers[check["id"]].noul,
                }
                for check in checks
            }
            results.append(
                {
                    "id": function["id"],
                    "file": function["file"],
                    "name": function["name"],
                    "qualified_name": function.get("qualified_name"),
                    "line": function.get("line"),
                    "end_line": function.get("end_line"),
                    "model": response.model,
                    "usage": usage,
                    "responses": responses,
                }
            )
    return results, total_usage, sorted(resolved_models)


def write_output(path: Path, report: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output_file:
        yaml.safe_dump(
            dict(report),
            output_file,
            sort_keys=False,
            allow_unicode=True,
            width=100,
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    data = load_json(args.input)
    check_config, checks = load_checks(args.checks)
    functions = validate_input(data)
    states = build_states(functions)
    payload = question_payload(checks)
    estimate = estimate_run(
        states,
        payload,
        args.fixed_tokens_per_request,
        args.price_per_million_input_tokens,
    )
    display_estimate(estimate)
    if args.estimate_only:
        return 0
    if not get_approval(args.yes):
        print("Jev calls cancelled. No output was written.")
        return 2
    if not os.environ.get("TYPESAFE_API_KEY"):
        print("TYPESAFE_API_KEY must be set before calling Jev.", file=sys.stderr)
        return 2

    started_at = datetime.now(timezone.utc)
    start_time = time.perf_counter()
    results, usage, resolved_models = run_reviews(states, functions, checks, args.model)
    duration_seconds = time.perf_counter() - start_time
    actual_cost = (
        usage["input_tokens"] * args.price_per_million_input_tokens / 1_000_000
    )
    completed_at = datetime.now(timezone.utc)
    report = {
        "schema_version": "1.0",
        "source": {
            "input_file": str(args.input.resolve()),
            "input_schema_version": data.get("schema_version"),
            "checks_file": str(args.checks.resolve()),
        },
        "run": {
            "requested_model": args.model,
            "resolved_models": resolved_models,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": round(duration_seconds, 6),
        },
        "cost": {
            "currency": "USD",
            "estimate": estimate,
            "actual_input_tokens": usage["input_tokens"],
            "actual_output_tokens": usage["output_tokens"],
            "actual_cost_usd": actual_cost,
            "note": "Cost uses input tokens only and the configured price assumption.",
        },
        "checks": check_config,
        "functions": results,
    }
    write_output(args.output, report)

    print(f"Output: {args.output.resolve()}")
    print(f"Actual input tokens: {usage['input_tokens']:,}")
    print(f"Actual cost: ${actual_cost:.8f}")
    print(f"Elapsed time: {duration_seconds:.3f} seconds")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
