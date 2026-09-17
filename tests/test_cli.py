from pathlib import Path

from rosters.cli import main


def test_main_prints_package_directory(capsys) -> None:
    main()

    output = capsys.readouterr().out.strip()
    assert Path(output) == Path(__file__).parents[1] / "src" / "rosters"
