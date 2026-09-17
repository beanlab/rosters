from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .preprocess import YPError, preprocess
from .runtime import run


def main(argv: Sequence[str] | None = None) -> int:
    """Run the YP command-line interface."""
    parser = _create_parser()
    arguments = parser.parse_args(argv)

    try:
        if arguments.compile:
            _compile_file(arguments.file, arguments.output)
        else:
            if arguments.output is not None:
                parser.error("-o/--output requires --compile")
            run(str(arguments.file))
    except (OSError, YPError) as error:
        parser.exit(1, f"yp: {error}\n")

    return 0


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yp", description="Preprocess and execute body-first Python functions."
    )
    parser.add_argument(
        "--compile", action="store_true", help="write Python instead of executing it"
    )
    parser.add_argument("file", type=Path, help="the .yp source file")
    parser.add_argument("-o", "--output", type=Path, help="output Python file")
    return parser


def _compile_file(source_path: Path, output_path: Path | None) -> None:
    generated = preprocess(
        source_path.read_text(encoding="utf-8"), str(source_path)
    )
    if output_path is None:
        sys.stdout.write(generated)
    else:
        output_path.write_text(generated, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
