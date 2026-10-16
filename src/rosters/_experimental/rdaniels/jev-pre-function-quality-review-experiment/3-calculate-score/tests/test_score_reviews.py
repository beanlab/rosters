import json
import tempfile
import unittest
from pathlib import Path

import yaml

from score_reviews import ScoringError, calculate_scores


class CalculateScoresTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.metadata_path = self.root / "parsed.json"
        self.review_path = self.root / "function-review.yaml"
        self.metadata_path.write_text(
            json.dumps(
                {
                    "functions": [
                        {"id": "src/a.py::top@1", "depth_to_leaf": 2},
                        {"id": "src/a.py::leaf@5", "depth_to_leaf": 0},
                        {"id": "test.py::test_a@1", "depth_to_leaf": 0},
                    ]
                }
            ),
            encoding="utf-8",
        )
        self.review = {
            "schema_version": "1.0",
            "source": {"input_file": str(self.metadata_path)},
            "checks": {
                "groups": [
                    {
                        "id": "readability",
                        "questions": [
                            {"id": "clear", "polarity": "positive"},
                            {"id": "confusing", "polarity": "negative"},
                        ],
                    }
                ]
            },
            "functions": [
                self.function("src/a.py::top@1", "src/a.py", 0.9, 0.1),
                self.function("src/a.py::leaf@5", "src/a.py", 0.8, 0.1),
                self.function("test.py::test_a@1", "test.py", 0.9, 0.9),
            ],
        }
        self.write_review()

    def tearDown(self):
        self.temporary_directory.cleanup()

    @staticmethod
    def function(function_id, file_name, probability_yes, confusing_probability_yes):
        return {
            "id": function_id,
            "file": file_name,
            "name": function_id.split("::")[1].split("@")[0],
            "qualified_name": function_id.split("::")[1].split("@")[0],
            "line": 1,
            "responses": {
                "clear": {
                    "probability_yes": probability_yes,
                    "probability_no": 1 - probability_yes,
                },
                "confusing": {
                    "probability_yes": confusing_probability_yes,
                    "probability_no": 1 - confusing_probability_yes,
                },
            },
        }

    def write_review(self):
        self.review_path.write_text(yaml.safe_dump(self.review), encoding="utf-8")

    def test_scores_every_level_and_category(self):
        result = calculate_scores(self.review_path)

        self.assertEqual(result["overall"]["basic"], {"score": 0.666667, "passed": 4, "total": 6})
        self.assertEqual(result["overall"]["weighted"]["score"], 0.8)
        self.assertEqual(result["overall"]["categories"]["readability"]["weighted"]["score"], 0.8)
        self.assertEqual([module["id"] for module in result["modules"]], [".", "src"])
        self.assertEqual(len(result["files"]), 2)
        self.assertEqual([function["weight"] for function in result["functions"]], [3, 1, 1])
        self.assertTrue(result["functions"][0]["criteria"]["clear"]["passed"])
        self.assertFalse(result["functions"][2]["criteria"]["confusing"]["passed"])

    def test_threshold_is_inclusive_and_configurable(self):
        self.review["functions"][0]["responses"]["clear"]["probability_yes"] = 0.85
        self.write_review()

        at_default = calculate_scores(self.review_path)
        above_default = calculate_scores(self.review_path, threshold=0.86)

        self.assertTrue(at_default["functions"][0]["criteria"]["clear"]["passed"])
        self.assertFalse(above_default["functions"][0]["criteria"]["clear"]["passed"])

    def test_rejects_missing_depth_metadata(self):
        self.review["functions"].append(self.function("src/a.py::missing@9", "src/a.py", 1, 0))
        self.write_review()

        with self.assertRaisesRegex(ScoringError, "No depth metadata"):
            calculate_scores(self.review_path)

    def test_rejects_invalid_threshold(self):
        with self.assertRaisesRegex(ScoringError, "between 0 and 1"):
            calculate_scores(self.review_path, threshold=1.1)


if __name__ == "__main__":
    unittest.main()
