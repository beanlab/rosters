import tempfile
import unittest
from pathlib import Path

from review_functions import (
    build_states,
    estimate_run,
    load_checks,
    question_payload,
    write_output,
)


class ReviewFunctionsTests(unittest.TestCase):
    def test_checks_are_valid_and_polarized(self) -> None:
        config, checks = load_checks(Path(__file__).with_name("code-checks.yaml"))

        self.assertEqual(config["schema_version"], "1.0")
        self.assertEqual(len(checks), 16)
        self.assertEqual({check["polarity"] for check in checks}, {"positive", "negative"})

    def test_states_include_file_and_class_context(self) -> None:
        functions = [
            {
                "id": "a.py::Box.first@1",
                "file": "a.py",
                "name": "first",
                "signature": "first(self)",
                "source": "def first(self): pass",
                "owner_class": "Box",
            },
            {
                "id": "a.py::Box.second@2",
                "file": "a.py",
                "name": "second",
                "signature": "second(self)",
                "source": "def second(self): pass",
                "owner_class": "Box",
            },
        ]

        state = build_states(functions)[0]

        self.assertEqual(state["target_function"]["id"], functions[0]["id"])
        self.assertEqual(state["related_context"]["other_file_function_count"], 1)
        self.assertEqual(
            state["related_context"]["other_file_functions"][0]["id"],
            functions[1]["id"],
        )
        self.assertEqual(state["related_context"]["owner_class_function_count"], 2)

    def test_estimate_is_deterministic(self) -> None:
        states = [{"target_function": {"source": "def f(): pass"}}]
        questions = {"readable": {"type": "noul", "instructions": "Readable?"}}

        estimate = estimate_run(states, questions, 200, 0.042)

        self.assertEqual(estimate["request_count"], 1)
        self.assertGreaterEqual(estimate["estimated_input_tokens"], 200)
        self.assertAlmostEqual(
            estimate["estimated_cost_usd"],
            estimate["estimated_input_tokens"] * 0.042 / 1_000_000,
        )

    def test_output_is_parseable_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "nested" / "report.yaml"
            write_output(output, {"schema_version": "1.0", "functions": []})

            import yaml

            loaded = yaml.safe_load(output.read_text(encoding="utf-8"))
            self.assertEqual(loaded["functions"], [])

    def test_question_payload_keeps_true_and_false_criteria(self) -> None:
        _, checks = load_checks(Path(__file__).with_name("code-checks.yaml"))

        payload = question_payload(checks)

        self.assertEqual(payload["easy_to_follow"]["type"], "noul")
        self.assertIn("true", payload["easy_to_follow"]["criteria"])
        self.assertIn("false", payload["easy_to_follow"]["criteria"])


if __name__ == "__main__":
    unittest.main()
