import json
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from function_index import analyze, analyze_revision, historical_cutoffs, resolve_commit, write_history


class AnalyzeTests(unittest.TestCase):
    def test_indexes_functions_and_calculates_depths(self):
        source = """\
def main():
    middle()

def middle():
    leaf()

def leaf():
    return 1

if __name__ == "__main__":
    main()
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "app.py").write_text(source, encoding="utf-8")

            result = analyze(root)

        functions = {item["name"]: item for item in result["functions"]}
        self.assertEqual(result["entry_points"], [functions["main"]["id"]])
        self.assertEqual(functions["main"]["depth_from_entry"], 0)
        self.assertEqual(functions["middle"]["depth_from_entry"], 1)
        self.assertEqual(functions["leaf"]["depth_from_entry"], 2)
        self.assertEqual(functions["main"]["depth_to_leaf"], 2)
        self.assertEqual(functions["middle"]["depth_to_leaf"], 1)
        self.assertEqual(functions["leaf"]["depth_to_leaf"], 0)
        self.assertIn("def leaf():", functions["leaf"]["source"])

    def test_resolves_methods_and_collapses_recursive_cycles(self):
        source = """\
class Worker:
    def start(self):
        self.loop()

    def loop(self):
        self.loop()

Worker().start()
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "worker.py").write_text(source, encoding="utf-8")

            result = analyze(root)

        functions = {item["name"]: item for item in result["functions"]}
        self.assertEqual(functions["start"]["calls"], [functions["loop"]["id"]])
        self.assertEqual(functions["loop"]["calls"], [functions["loop"]["id"]])
        self.assertEqual(functions["loop"]["depth_to_leaf"], 0)

    def test_resolves_a_nested_function_call(self):
        source = """\
def outer():
    def inner():
        return 1
    return inner()

outer()
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "nested.py").write_text(source, encoding="utf-8")

            result = analyze(root)

        functions = {item["name"]: item for item in result["functions"]}
        self.assertEqual(functions["outer"]["calls"], [functions["inner"]["id"]])
        self.assertEqual(functions["inner"]["depth_from_entry"], 1)


@unittest.skipUnless(shutil.which("git"), "Git is required")
class HistoricalAnalyzeTests(unittest.TestCase):
    def git(self, repository, *arguments, date=None):
        environment = os.environ.copy()
        if date:
            environment["GIT_AUTHOR_DATE"] = date
            environment["GIT_COMMITTER_DATE"] = date
        return subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
            env=environment,
        )

    def make_repository(self, directory):
        repository = Path(directory)
        self.git(repository, "init", "-b", "main")
        self.git(repository, "config", "user.name", "Test User")
        self.git(repository, "config", "user.email", "test@example.com")

        (repository / "app.py").write_text("def january():\n    return 1\n", encoding="utf-8")
        self.git(repository, "add", "app.py")
        self.git(repository, "commit", "-m", "January", date="2024-01-10T12:00:00+00:00")

        (repository / "app.py").write_text("def march():\n    return 3\n", encoding="utf-8")
        self.git(repository, "add", "app.py")
        self.git(repository, "commit", "-m", "March", date="2024-03-10T12:00:00+00:00")
        return repository

    def test_generates_weekly_monthly_and_bimonthly_cutoffs(self):
        now = datetime(2024, 5, 31, 12, tzinfo=timezone.utc)

        weekly = historical_cutoffs("weekly", 2, now)
        monthly = historical_cutoffs("monthly", 3, now)
        bimonthly = historical_cutoffs("bimonthly", 2, now)

        self.assertEqual([value.day for value in weekly], [31, 24])
        self.assertEqual([(value.month, value.day) for value in monthly], [(5, 31), (4, 30), (3, 31)])
        self.assertEqual([(value.month, value.day) for value in bimonthly], [(5, 31), (3, 31)])

    def test_analyzes_repository_at_a_cutoff_without_changing_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = self.make_repository(directory)
            head_before = self.git(repository, "rev-parse", "HEAD").stdout

            result = analyze_revision(
                repository,
                "main",
                datetime(2024, 2, 1, tzinfo=timezone.utc),
            )

            head_after = self.git(repository, "rev-parse", "HEAD").stdout

        self.assertEqual([function["name"] for function in result["functions"]], ["january"])
        self.assertEqual(result["git"]["ref"], "main")
        self.assertEqual(head_before, head_after)

    def test_missing_ref_tells_user_to_fetch(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = self.make_repository(directory)

            with self.assertRaisesRegex(ValueError, "Fetch the branch"):
                resolve_commit(repository, "missing", datetime.now(timezone.utc))

    def test_writes_requested_history_results(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as output_directory:
            repository = self.make_repository(directory)

            outputs = write_history(repository, "main", "monthly", 1, Path(output_directory))
            result = json.loads(outputs[0].read_text(encoding="utf-8"))

        self.assertEqual(len(outputs), 1)
        self.assertEqual(result["git"]["ref"], "main")
        self.assertEqual([function["name"] for function in result["functions"]], ["march"])

    def test_shallow_history_tells_user_to_unshallow(self):
        with tempfile.TemporaryDirectory() as source_directory, tempfile.TemporaryDirectory() as clone_parent:
            source = self.make_repository(source_directory)
            clone = Path(clone_parent) / "clone"
            subprocess.run(
                ["git", "clone", "--depth=1", f"file://{source}", str(clone)],
                check=True,
                capture_output=True,
            )

            with self.assertRaisesRegex(ValueError, "fetch --unshallow"):
                resolve_commit(clone, "HEAD", datetime(2024, 2, 1, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
