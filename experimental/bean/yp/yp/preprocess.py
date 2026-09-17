from __future__ import annotations

import keyword
import re
from dataclasses import dataclass


class YPError(ValueError):
    """An error in YP source code."""


def preprocess(source: str, filename: str = "<yp>") -> str:
    """Transform body-first YP function declarations into Python source."""
    lines = source.splitlines(keepends=True)
    functions = _find_functions(lines)
    generated = _apply_dependencies(lines, functions)
    _validate_python(generated, filename)
    return generated


@dataclass(frozen=True)
class _Function:
    line_index: int
    indentation: int
    indentation_text: str
    name: str
    dependency_line_index: int
    dependencies: str


@dataclass(frozen=True)
class _OpenFunction:
    line_index: int
    indentation: int
    indentation_text: str
    name: str


_HEADER = re.compile(r"def[ \t]+([^\s:]+)[ \t]*:[ \t]*(?:\r?\n)?$")


def _find_functions(lines: list[str]) -> list[_Function]:
    open_functions: list[_OpenFunction] = []
    functions: list[_Function] = []

    for line_index, line in enumerate(lines):
        if _is_blank(line):
            continue

        indentation_text, content = _split_indentation(line)
        indentation = _indentation_width(indentation_text)

        if _is_needs_line(content):
            _close_with_dependencies(
                line_index,
                indentation,
                indentation_text,
                content,
                open_functions,
                functions,
            )
            continue

        _reject_unclosed_functions(line_index, indentation, open_functions)

        if content.startswith("def ") or content.startswith("def\t"):
            open_functions.append(
                _parse_header(line_index, indentation, indentation_text, content)
            )

    if open_functions:
        function = open_functions[-1]
        raise YPError(
            f"line {len(lines) + 1}: missing needs clause for function {function.name}"
        )

    return functions


def _apply_dependencies(lines: list[str], functions: list[_Function]) -> str:
    replacements: dict[int, str] = {}
    for function in functions:
        header = lines[function.line_index]
        line_ending = _line_ending(header)
        replacements[function.line_index] = (
            f"{function.indentation_text}def {function.name}"
            f"{function.dependencies}:{line_ending}"
        )
        replacements[function.dependency_line_index] = _line_ending(
            lines[function.dependency_line_index]
        )

    return "".join(replacements.get(index, line) for index, line in enumerate(lines))


def _validate_python(source: str, filename: str) -> None:
    try:
        compile(source, filename, "exec")
    except SyntaxError as error:
        line_number = error.lineno or 1
        detail = error.msg or str(error)
        raise YPError(
            f"line {line_number}: generated Python is invalid: {detail}"
        ) from error


def _close_with_dependencies(
    line_index: int,
    indentation: int,
    indentation_text: str,
    content: str,
    open_functions: list[_OpenFunction],
    functions: list[_Function],
) -> None:
    if not open_functions:
        raise YPError(f"line {line_index + 1}: unexpected needs clause")

    function = open_functions[-1]
    if indentation < function.indentation:
        raise YPError(
            f"line {line_index + 1}: missing needs clause for function {function.name}"
        )
    if indentation != function.indentation:
        raise YPError(
            f"line {line_index + 1}: needs clause must be at the same indentation as def"
        )

    clause = _without_line_ending(content)
    dependencies = clause[len("needs") :].lstrip(" \t")
    if not dependencies.strip():
        raise YPError(f"line {line_index + 1}: empty needs clause")

    open_functions.pop()
    functions.append(
        _Function(
            line_index=function.line_index,
            indentation=function.indentation,
            indentation_text=function.indentation_text,
            name=function.name,
            dependency_line_index=line_index,
            dependencies=dependencies,
        )
    )


def _reject_unclosed_functions(
    line_index: int, indentation: int, open_functions: list[_OpenFunction]
) -> None:
    if open_functions and indentation <= open_functions[-1].indentation:
        function = open_functions[-1]
        raise YPError(
            f"line {line_index + 1}: missing needs clause for function {function.name}"
        )


def _parse_header(
    line_index: int, indentation: int, indentation_text: str, content: str
) -> _OpenFunction:
    match = _HEADER.fullmatch(content)
    if not match:
        raise YPError(
            f"line {line_index + 1}: expected function header of the form 'def NAME:'"
        )
    name = match.group(1)
    if not name.isidentifier() or keyword.iskeyword(name):
        raise YPError(
            f"line {line_index + 1}: expected function header of the form 'def NAME:'"
        )
    return _OpenFunction(line_index, indentation, indentation_text, name)


def _is_needs_line(content: str) -> bool:
    return content == "needs" or content.startswith(
        ("needs ", "needs\t", "needs\n", "needs\r")
    )


def _is_blank(line: str) -> bool:
    return not line.strip()


def _split_indentation(line: str) -> tuple[str, str]:
    stripped = line.lstrip(" \t")
    return line[: len(line) - len(stripped)], stripped


def _indentation_width(indentation: str) -> int:
    return len(indentation.expandtabs(8))


def _without_line_ending(line: str) -> str:
    ending = _line_ending(line)
    return line[: -len(ending)] if ending else line


def _line_ending(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    return ""
