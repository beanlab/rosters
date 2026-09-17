from yp.cli import main
from yp.runtime import run


def test_compile_writes_python(tmp_path):
    source = tmp_path / "example.yp"
    output = tmp_path / "example.py"
    source.write_text("def answer:\n    return 42\nneeds ()\n")

    assert main(["--compile", str(source), "-o", str(output)]) == 0
    assert output.read_text() == "def answer():\n    return 42\n\n"


def test_compile_uses_utf8_and_stdout_by_default(tmp_path, capsys):
    source = tmp_path / "unicode.yp"
    source.write_text(
        "def café:\n    return 'こんにちは'\nneeds ()\n", encoding="utf-8"
    )

    assert main(["--compile", str(source)]) == 0
    assert capsys.readouterr().out == "def café():\n    return 'こんにちは'\n\n"


def test_run_accepts_path_and_reads_utf8(tmp_path, capsys):
    source = tmp_path / "unicode.yp"
    source.write_text(
        "def greet:\n    print(message)\nneeds (message)\n\ngreet('こんにちは')\n",
        encoding="utf-8",
    )

    run(source)
    assert capsys.readouterr().out == "こんにちは\n"


def test_run_executes_as_main(tmp_path, capsys):
    source = tmp_path / "example.yp"
    source.write_text(
        "def greet:\n"
        "    print(message)\n"
        "needs (message)\n"
        "\n"
        "greet('hello')\n"
    )

    assert main([str(source)]) == 0
    assert capsys.readouterr().out == "hello\n"
