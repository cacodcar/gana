"""
Safety and comparison checks for the baseline runner (standard-library only).
"""

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import baseline


class BaselineTests(unittest.TestCase):
    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            sentinel = Path(directory) / "summary.json"
            sentinel.write_text("keep this report")
            with patch.object(baseline, "check_environment", return_value={}):
                with patch("sys.argv", ["baseline", "--output", directory]):
                    with self.assertRaises(FileExistsError):
                        baseline.main()
            self.assertEqual(sentinel.read_text(), "keep this report")

    def test_failed_commands_keep_diagnostics_and_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result, _ = baseline.run_command(
                "failure",
                ["_gana_intentionally_missing_module"],
                output,
                {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                output,
            )
            self.assertNotEqual(result["exit_code"], 0)
            self.assertIn(
                "No module named",
                (output / "failure.stderr.txt").read_text(),
            )

    def test_replay_detects_source_environment_and_metric_changes(self):
        original = {
            "python": "3.13.7",
            "platform": "reference",
            "machine": "x86_64",
            "packages": {"pytest": "8.4.2"},
            "seed": "20260921",
            "environment": {},
            "interpreter": "/original/python",
            "created_utc": "old",
        }
        hashes = {"src/gana/__init__.py": "abc"}
        metrics = {"tests": {"tests": 14, "failures": 0}}
        with tempfile.TemporaryDirectory() as directory:
            reference, output = (
                Path(directory) / "reference",
                Path(directory) / "output",
            )
            reference.mkdir()
            output.mkdir()
            baseline.write_json(reference / "manifest.json", original)
            baseline.write_json(reference / "source-hashes.json", hashes)
            baseline.write_json(reference / "summary.json", metrics)
            for change in (None, "source", "environment", "metrics"):
                with self.subTest(change=change):
                    current = {
                        **original,
                        "interpreter": "/rebuilt/python",
                        "created_utc": "new",
                    }
                    if change == "environment":
                        current["packages"] = {"pytest": "other-version"}
                    baseline.write_json(output / "manifest.json", current)
                    inputs = {} if change == "source" else hashes
                    values = {} if change == "metrics" else metrics
                    with contextlib.redirect_stdout(io.StringIO()):
                        matches = baseline.compare(
                            reference,
                            output,
                            inputs,
                            values,
                        )
                    self.assertEqual(matches, change is None)
                    self.assertEqual(
                        json.loads((output / "comparison.json").read_text())[
                            "same_source"
                        ],
                        change != "source",
                    )


class BaselineOrchestrationTests(unittest.TestCase):
    """Exercise a whole run without invoking a nested test suite."""

    def test_failed_metric_keeps_other_checks_and_failed_run(self):
        """Keep tests and diagnostics after failure; return a failed status."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "sample.py"
            source.write_text('"""Reference input."""\n')
            lock = root / "reference.lock"
            lock.write_text("reference\n")
            output = root / "run"
            commands = []

            def recorded_command(name, arguments, work, env, destination):
                """Simulate a metric failure and retain the command record."""
                commands.append(name)
                code = 2 if name == "maintainability" else 0
                payload = json.dumps({str(source): {}})
                (destination / f"{name}.stderr.txt").write_text(
                    "metric failure" if code else "",
                )
                self.assertEqual(env["PYTHONHASHSEED"], "0")
                self.assertEqual(
                    env["PYTEST_FUNCTION_PROFILE_OUTPUT"],
                    str(output / "profile"),
                )
                return {"command": arguments, "exit_code": code}, payload

            with contextlib.ExitStack() as stack:
                for name, value in {
                    "ROOT": root,
                    "LOCK": lock,
                    "check_environment": lambda: {},
                    "source_files": lambda: [source],
                    "git": lambda *_args: "recorded",
                    "run_command": recorded_command,
                }.items():
                    stack.enter_context(patch.object(baseline, name, value))
                stack.enter_context(
                    patch("sys.argv", ["baseline", "--output", str(output)]),
                )
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                status = baseline.main()
            self.assertEqual(status, 1)
            self.assertEqual(
                commands,
                [
                    "complexity",
                    "maintainability",
                    "raw",
                    "complexity-b-or-worse",
                    "pytest",
                ],
            )
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertTrue(manifest["source_unchanged"])
            self.assertEqual(
                manifest["commands"]["maintainability"]["exit_code"],
                2,
            )
            self.assertEqual(
                (output / "maintainability.stderr.txt").read_text(),
                "metric failure",
            )
            self.assertTrue((output / "source.tar.gz").is_file())
            self.assertEqual(
                json.loads((output / "summary.json").read_text()),
                {},
            )


class BaselineInputTests(unittest.TestCase):
    """Validate provenance command boundaries and restricted JUnit parsing."""

    def test_git_uses_absolute_executable_and_separate_arguments(self):
        """Paths containing spaces remain one argument without a shell."""
        executable = baseline.ROOT / "mock git"
        with patch.object(
            baseline.shutil,
            "which",
            return_value=str(executable),
        ):
            with patch.object(
                baseline.subprocess,
                "check_output",
                return_value="main\n",
            ) as run:
                self.assertEqual(
                    baseline.git("branch", "--show-current"), "main"
                )
        run.assert_called_once_with(
            [str(executable.resolve()), "branch", "--show-current"],
            cwd=baseline.ROOT,
            text=True,
            shell=False,
        )

    def test_missing_git_fails_before_execution(self):
        """Missing Git must not produce incomplete provenance silently."""
        with patch.object(baseline.shutil, "which", return_value=None):
            with self.assertRaisesRegex(FileNotFoundError, "Git is required"):
                baseline.git("status", "--short")

    def test_junit_counts_and_encodings(self):
        """Aggregate suites and honor missing counters and XML encodings."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            for encoding in ("utf-8", "utf-16"):
                with self.subTest(encoding=encoding):
                    xml = (
                        f'<?xml version="1.0" encoding="{encoding}"?>'
                        '<testsuites><testsuite tests="3" failures="1" '
                        'name="a &amp; b" skipped="2"/>'
                        '<testsuite tests="2" errors="1"/></testsuites>'
                    )
                    (output / "pytest.xml").write_bytes(xml.encode(encoding))
                    self.assertEqual(
                        baseline.test_summary(output),
                        {
                            "tests": {
                                "tests": 5,
                                "failures": 1,
                                "errors": 1,
                                "skipped": 2,
                            }
                        },
                    )

    def test_junit_rejects_internal_and_external_dtds(self):
        """Reject entity declarations even when encoded as UTF-16."""
        declarations = (
            '<!DOCTYPE testsuite [<!ENTITY count "999">]>',
            '<!DOCTYPE testsuite SYSTEM "file:///nonexistent-junit.dtd">',
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            for declaration in declarations:
                for encoding in ("utf-8", "utf-16"):
                    with self.subTest(xml=declaration, encoding=encoding):
                        xml = (
                            f'<?xml version="1.0" encoding="{encoding}"?>'
                            f'{declaration}<testsuite tests="1"/>'
                        )
                        (output / "pytest.xml").write_bytes(
                            xml.encode(encoding)
                        )
                        with self.assertRaisesRegex(
                            ValueError, "DTD and entity"
                        ):
                            baseline.test_summary(output)

    def test_junit_namespaces_and_malformed_input(self):
        """Keep the old bare-name selection and fail on truncated reports."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            junit = output / "pytest.xml"
            junit.write_text('<testsuite xmlns="urn:other" tests="8"/>')
            self.assertEqual(baseline.test_summary(output), {"tests": {}})
            junit.write_text('<testsuite tests="1">')
            with self.assertRaises(baseline.expat.ExpatError):
                baseline.test_summary(output)


if __name__ == "__main__":
    unittest.main()
