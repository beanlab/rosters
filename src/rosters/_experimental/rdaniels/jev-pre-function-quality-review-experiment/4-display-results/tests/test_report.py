from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from generate_report import parse_input
from quality_report.generator import build_report
from quality_report.model import ScoreFileError, ScoreInput, load_project


def score(value: float, passed: int = 1, total: int = 1) -> dict[str, object]:
    return {"score": value, "passed": passed, "total": total}


def fixture_data() -> dict[str, object]:
    category = {"basic": score(0.5, 1, 2), "weighted": {"score": 0.4}}
    scores = {
        "basic": score(0.5, 1, 2),
        "weighted": {"score": 0.4},
        "categories": {"new_metric": category},
    }
    function_scores = json.loads(json.dumps(scores))
    return {
        "schema_version": "1.0",
        "scoring": {"threshold": 0.85},
        "overall": scores,
        "modules": [{"id": ".", "files": ["src/a.py"], "scores": scores}],
        "files": [
            {
                "id": "src/a.py",
                "module": ".",
                "functions": ["src/a.py::run@3"],
                "scores": scores,
            }
        ],
        "functions": [
            {
                "id": "src/a.py::run@3",
                "file": "src/a.py",
                "module": ".",
                "name": "run",
                "qualified_name": "run",
                "line": 3,
                "weight": 1,
                "scores": function_scores,
                "criteria": {
                    "new_check": {
                        "category": "new_metric",
                        "polarity": "positive",
                        "favorable_answer": "yes",
                        "favorable_probability": 0.5,
                        "passed": False,
                    }
                },
            }
        ],
    }


class ModelTests(unittest.TestCase):
    def test_discovers_categories_and_criteria(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scores.yaml"
            path.write_text(yaml.safe_dump(fixture_data()), encoding="utf-8")

            project = load_project(ScoreInput(path, "Example"))

        self.assertEqual(project["name"], "Example")
        self.assertEqual(project["categories"], ["new_metric"])
        self.assertEqual(project["criteria"]["new_check"]["category"], "new_metric")

    def test_rejects_missing_sections(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scores.yaml"
            path.write_text("overall: {}\n", encoding="utf-8")
            with self.assertRaisesRegex(ScoreFileError, "missing required keys"):
                load_project(ScoreInput(path))

    def test_named_cli_input(self) -> None:
        parsed = parse_input("Parser=C:/results/scores.yaml")
        self.assertEqual(parsed.name, "Parser")
        self.assertEqual(parsed.path, Path("C:/results/scores.yaml"))

    def test_joins_function_source_from_parser_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata_path = root / "parsed.json"
            metadata_path.write_text(
                json.dumps(
                    {
                        "git": {"cutoff": "2026-08-14T12:00:00+00:00"},
                        "functions": [
                            {
                                "id": "src/a.py::run@3",
                                "source": "def run():\n    return 1",
                                "signature": "run()",
                                "end_line": 4,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            data = fixture_data()
            data["source"] = {"function_metadata_file": "parsed.json"}
            score_path = root / "scores.yaml"
            score_path.write_text(yaml.safe_dump(data), encoding="utf-8")

            project = load_project(ScoreInput(score_path))

        function = project["functions"][0]
        self.assertEqual(project["capturedAt"], "2026-08-14T12:00:00+00:00")
        self.assertEqual(function["source"], "def run():\n    return 1")
        self.assertEqual(function["end_line"], 4)


class GeneratorTests(unittest.TestCase):
    def test_builds_one_self_contained_report_for_multiple_projects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.yaml"
            second = root / "second.yaml"
            output = root / "report.html"
            first.write_text(yaml.safe_dump(fixture_data()), encoding="utf-8")
            second.write_text(yaml.safe_dump(fixture_data()), encoding="utf-8")

            build_report(
                [ScoreInput(first, "First"), ScoreInput(second, "Second")],
                output,
                "Quality <Atlas>",
            )
            html = output.read_text(encoding="utf-8")

        self.assertIn("<title>Quality &lt;Atlas&gt;</title>", html)
        self.assertIn('"name":"First"', html)
        self.assertIn('"name":"Second"', html)
        self.assertIn('data-value="functions"', html)
        self.assertIn('data-view="history"', html)
        self.assertIn("Overall score over time", html)
        self.assertIn('id="history-chart"', html)
        self.assertIn('class="breadcrumbs"', html)
        self.assertIn("Function source", html)
        self.assertIn('class="criterion__status">${status}${percentage}', html)
        self.assertIn("data-toggle-criterion-percentages", html)
        self.assertIn("Show percentages", html)
        self.assertNotIn("favorable · expected", html)
        self.assertNotIn("<script src=", html)
        self.assertNotIn("<link rel=", html)


if __name__ == "__main__":
    unittest.main()
