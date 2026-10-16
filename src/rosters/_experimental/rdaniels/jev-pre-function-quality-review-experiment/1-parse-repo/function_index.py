#!/usr/bin/env python3
"""Index Python functions and their positions in a local call graph."""

from __future__ import annotations

import argparse
import ast
import calendar
import io
import json
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

import networkx as nx


SCHEMA_VERSION = "1.1"
EXCLUDED_DIRECTORIES = {".git", ".hg", ".mypy_cache", ".pytest_cache", ".tox", ".venv", "__pycache__", "venv"}


@dataclass(frozen=True)
class FunctionInfo:
    id: str
    file: str
    name: str
    qualified_name: str
    line: int
    end_line: int
    signature: str
    source: str
    owner_class: str | None
    enclosing_functions: tuple[str, ...]
    node: ast.FunctionDef | ast.AsyncFunctionDef


class FunctionCollector(ast.NodeVisitor):
    def __init__(self, file: str, source: str) -> None:
        self.file = file
        self.source = source
        self.functions: list[FunctionInfo] = []
        self._names: list[str] = []
        self._classes: list[str] = []
        self._functions: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._names.append(node.name)
        self._classes.append(".".join(self._names))
        self.generic_visit(node)
        self._classes.pop()
        self._names.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self._names.append(node.name)
        qualified_name = ".".join(self._names)
        function_id = f"{self.file}::{qualified_name}@{node.lineno}"
        self.functions.append(
            FunctionInfo(
                id=function_id,
                file=self.file,
                name=node.name,
                qualified_name=qualified_name,
                line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                signature=f"{node.name}({ast.unparse(node.args)})",
                source=ast.get_source_segment(self.source, node) or "",
                owner_class=self._classes[-1] if self._classes else None,
                enclosing_functions=tuple(self._functions),
                node=node,
            )
        )
        self._functions.append(qualified_name)
        self.generic_visit(node)
        self._functions.pop()
        self._names.pop()


class CallCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.calls: list[ast.Call] = []

    def visit_Call(self, node: ast.Call) -> None:
        self.calls.append(node)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return


def iter_python_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*.py")):
        if not any(part in EXCLUDED_DIRECTORIES or part.startswith(".") for part in path.relative_to(root).parts):
            yield path


def collect_calls(nodes: Iterable[ast.stmt]) -> list[ast.Call]:
    collector = CallCollector()
    for node in nodes:
        collector.visit(node)
    return collector.calls


def unique_symbol(symbols: dict[str, list[FunctionInfo]], name: str) -> FunctionInfo | None:
    matches = symbols.get(name, [])
    return matches[0] if len(matches) == 1 else None


def resolve_call(
    call: ast.Call,
    caller: FunctionInfo | None,
    symbols: dict[str, list[FunctionInfo]],
) -> FunctionInfo | None:
    target = call.func
    if isinstance(target, ast.Name):
        if caller is not None:
            scopes = (*caller.enclosing_functions, caller.qualified_name)
            for enclosing in reversed(scopes):
                match = unique_symbol(symbols, f"{enclosing}.{target.id}")
                if match is not None:
                    return match
        return unique_symbol(symbols, target.id)

    if (
        caller is not None
        and caller.owner_class is not None
        and isinstance(target, ast.Attribute)
        and isinstance(target.value, ast.Name)
        and target.value.id in {"self", "cls"}
    ):
        return unique_symbol(symbols, f"{caller.owner_class}.{target.attr}")

    return None


def bottom_depths(graph: nx.DiGraph) -> dict[str, int]:
    if not graph:
        return {}
    condensed = nx.condensation(graph)
    component_depth: dict[int, int] = {}
    for component in reversed(list(nx.topological_sort(condensed))):
        children = list(condensed.successors(component))
        component_depth[component] = 0 if not children else 1 + max(component_depth[child] for child in children)
    return {
        function_id: component_depth[component]
        for function_id, component in condensed.graph["mapping"].items()
    }


def analyze(root: Path) -> dict[str, object]:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"not a directory: {root}")

    functions: list[FunctionInfo] = []
    modules: list[tuple[str, ast.Module]] = []
    errors: list[dict[str, object]] = []

    for path in iter_python_files(root):
        relative_path = path.relative_to(root).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=relative_path)
        except (OSError, UnicodeError, SyntaxError) as error:
            errors.append({"file": relative_path, "error": str(error)})
            continue
        collector = FunctionCollector(relative_path, source)
        collector.visit(tree)
        functions.extend(collector.functions)
        modules.append((relative_path, tree))

    symbols_by_file: dict[str, dict[str, list[FunctionInfo]]] = {}
    for function in functions:
        file_symbols = symbols_by_file.setdefault(function.file, {})
        file_symbols.setdefault(function.qualified_name, []).append(function)

    graph = nx.DiGraph()
    graph.add_nodes_from(function.id for function in functions)
    calls_by_function: dict[str, set[str]] = {function.id: set() for function in functions}
    entry_points: set[str] = set()

    for function in functions:
        symbols = symbols_by_file[function.file]
        for call in collect_calls(function.node.body):
            target = resolve_call(call, function, symbols)
            if target is not None:
                graph.add_edge(function.id, target.id)
                calls_by_function[function.id].add(target.id)

    for file, tree in modules:
        symbols = symbols_by_file.get(file, {})
        for call in collect_calls(tree.body):
            target = resolve_call(call, None, symbols)
            if target is not None:
                entry_points.add(target.id)

    entry_depths = (
        nx.multi_source_dijkstra_path_length(graph, entry_points, weight=None)
        if entry_points
        else {}
    )
    leaf_depths = bottom_depths(graph)

    records = []
    for function in sorted(functions, key=lambda item: (item.file, item.line, item.qualified_name)):
        records.append(
            {
                "id": function.id,
                "file": function.file,
                "name": function.name,
                "qualified_name": function.qualified_name,
                "line": function.line,
                "end_line": function.end_line,
                "signature": function.signature,
                "source": function.source,
                "calls": sorted(calls_by_function[function.id]),
                "depth_from_entry": entry_depths.get(function.id),
                "depth_to_leaf": leaf_depths[function.id],
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "root": str(root),
        "entry_points": sorted(entry_points),
        "functions": records,
        "errors": errors,
    }


def subtract_months(value: datetime, months: int) -> datetime:
    month_index = value.year * 12 + value.month - 1 - months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def historical_cutoffs(interval: str, count: int, now: datetime | None = None) -> list[datetime]:
    if count < 1:
        raise ValueError("--count must be at least 1")
    now = now or datetime.now().astimezone()
    if interval == "weekly":
        return [now - timedelta(weeks=index) for index in range(count)]
    months = 1 if interval == "monthly" else 2
    return [subtract_months(now, months * index) for index in range(count)]


def run_git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", "-C", str(repository), *arguments],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as error:
        raise ValueError("Git is required for historical analysis but was not found") from error


def resolve_commit(repository: Path, ref: str, cutoff: datetime) -> str:
    verified = run_git(repository, "rev-parse", "--verify", f"{ref}^{{commit}}")
    if verified.returncode != 0:
        raise ValueError(
            f"Git ref {ref!r} was not found in {repository}. "
            "Fetch the branch or choose a ref that exists locally."
        )

    result = run_git(repository, "rev-list", "-1", f"--before={cutoff.isoformat()}", ref)
    commit = result.stdout.decode("utf-8").strip()
    if result.returncode == 0 and commit:
        return commit

    shallow = run_git(repository, "rev-parse", "--is-shallow-repository")
    if shallow.stdout.decode("utf-8").strip() == "true":
        raise ValueError(
            f"The shallow clone does not contain history as far back as {cutoff.isoformat()}. "
            f"Run: git -C {repository} fetch --unshallow"
        )
    raise ValueError(f"No commit on {ref!r} exists at or before {cutoff.isoformat()}")


def extract_python_archive(archive: bytes, destination: Path) -> None:
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as source:
        for member in source.getmembers():
            path = Path(member.name)
            if not member.isfile() or path.suffix != ".py":
                continue
            if any(part in EXCLUDED_DIRECTORIES or part.startswith(".") for part in path.parts):
                continue
            extracted = source.extractfile(member)
            if extracted is None:
                continue
            output = destination / path
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(extracted.read())


def analyze_revision(repository: Path, ref: str, cutoff: datetime) -> dict[str, object]:
    repository = repository.resolve()
    if not repository.is_dir():
        raise ValueError(f"not a directory: {repository}")
    commit = resolve_commit(repository, ref, cutoff)
    archive = run_git(repository, "archive", "--format=tar", commit)
    if archive.returncode != 0:
        message = archive.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"Could not read commit {commit}: {message}")

    with tempfile.TemporaryDirectory() as directory:
        snapshot = Path(directory)
        extract_python_archive(archive.stdout, snapshot)
        result = analyze(snapshot)

    result["root"] = str(repository)
    result["git"] = {
        "ref": ref,
        "commit": commit,
        "cutoff": cutoff.isoformat(),
    }
    return result


def write_history(
    repository: Path,
    ref: str,
    interval: str,
    count: int,
    output_directory: Path,
) -> list[Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    outputs = []
    for cutoff in historical_cutoffs(interval, count):
        result = analyze_revision(repository, ref, cutoff)
        commit = result["git"]["commit"]
        timestamp = cutoff.strftime("%Y-%m-%dT%H%M%S%z")
        output = output_directory / f"functions-{timestamp}-{commit[:12]}.json"
        output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        outputs.append(output)
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="local Python repository or directory")
    parser.add_argument("-o", "--output", type=Path, help="write JSON to this file instead of stdout")
    parser.add_argument("--ref", default="HEAD", help="local branch or Git ref to analyze")
    parser.add_argument("--interval", choices=("weekly", "monthly", "bimonthly"))
    parser.add_argument("--count", type=int, help="number of historical snapshots")
    parser.add_argument("--output-dir", type=Path, help="directory for historical JSON files")
    args = parser.parse_args()

    historical_options = args.count is not None or args.output_dir is not None or args.ref != "HEAD"
    if args.interval is None and historical_options:
        parser.error("--ref, --count, and --output-dir require --interval")
    if args.interval is not None:
        if args.count is None or args.output_dir is None:
            parser.error("--interval requires --count and --output-dir")
        if args.output is not None:
            parser.error("--output cannot be used with --interval; use --output-dir")
        if args.count < 1:
            parser.error("--count must be at least 1")
    return args


def main() -> None:
    args = parse_args()
    try:
        if args.interval:
            outputs = write_history(args.directory, args.ref, args.interval, args.count, args.output_dir)
            for output in outputs:
                print(output)
        else:
            result = analyze(args.directory)
            encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
            if args.output:
                args.output.write_text(encoded, encoding="utf-8")
            else:
                print(encoded, end="")
    except ValueError as error:
        raise SystemExit(f"error: {error}") from error


if __name__ == "__main__":
    main()
