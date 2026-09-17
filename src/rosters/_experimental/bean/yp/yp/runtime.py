from __future__ import annotations

from pathlib import Path

from .preprocess import preprocess


def run(path: str | Path) -> None:
    """Transform and execute a YP file as the main module."""
    source_path = Path(path)
    source = preprocess(
        source_path.read_text(encoding="utf-8"), str(source_path)
    )
    code = compile(source, str(source_path), "exec")
    namespace = {
        "__name__": "__main__",
        "__file__": str(source_path),
    }
    exec(code, namespace)
