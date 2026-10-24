"""Verify profile attribution, comparison safeguards and real pytest hooks."""

import os
from pathlib import Path
from unittest import TestCase

import pytest

from profile_stats import (
    Symbols,
    compare_reports,
    file_hashes,
    fingerprint,
    function_rows,
    named_functions,
    prior_report,
    read_json,
    write_json,
)

pytest_plugins = ["pytester"]

CHECK = TestCase()
ROOT = Path(__file__).resolve().parents[1]


def recorded_report():
    """Provide a small independent profile with explicit comparison inputs."""
    return {
        "eligible": True,
        "comparison_inputs": {
            "tests": ["test_x"],
            "environment": "same",
            "instrumentation": "same",
        },
        "functions": [
            {
                "id": "gana/x.py::work",
                "project": True,
                "calls": 2,
                "self_seconds": 1.0,
                "cumulative_seconds": 3.0,
            },
        ],
    }


def test_compare_calls_and_self_cost():
    """More calls and more cost per call remain distinct signals."""
    before, after = recorded_report(), recorded_report()
    after["functions"][0].update(
        calls=4,
        self_seconds=6.0,
        cumulative_seconds=9.0,
    )
    row = compare_reports(before, after)["functions"][0]
    CHECK.assertEqual(row["calls"]["delta"], 2)
    CHECK.assertEqual(row["self_seconds"]["delta"], 5)
    CHECK.assertEqual(
        row["self_seconds_per_call"],
        {"before": 0.5, "after": 1.5},
    )


@pytest.mark.parametrize("field", ["tests", "environment", "instrumentation"])
def test_incompatible_inputs_have_no_time_deltas(field):
    """
    Changing workloads, hosts or instrumentation cannot yield a speed claim.
    """
    before, after = recorded_report(), recorded_report()
    after["comparison_inputs"][field] = "changed"
    result = compare_reports(before, after)
    CHECK.assertEqual(result["status"], "incompatible")
    CHECK.assertEqual(result["changed_inputs"], [field])
    CHECK.assertNotIn("functions", result)


def test_failed_reference_is_not_a_baseline():
    """
    A fast but failing reference is ineligible even when its inputs match.
    """
    before = recorded_report()
    before["eligible"] = False
    CHECK.assertEqual(
        compare_reports(before, recorded_report())["status"],
        "incomplete",
    )


def test_added_removed_functions_and_duplicate_code_objects():
    """New, removed and multiply-loaded functions retain full counters."""
    before, after = recorded_report(), recorded_report()
    before["functions"].append(dict(before["functions"][0]))
    after["functions"][0]["id"] = "gana/x.py::new"
    result = compare_reports(before, after)["functions"]
    rows = {row["id"]: row for row in result}
    CHECK.assertEqual(rows["gana/x.py::work"]["calls"]["delta"], -4)
    CHECK.assertEqual(rows["gana/x.py::new"]["calls"]["delta"], 2)
    CHECK.assertIsNone(
        rows["gana/x.py::new"]["self_seconds_per_call"]["before"],
    )


def test_function_identity_survives_moved_lines(tmp_path):
    """
    Qualified project names distinguish methods and survive added comments.
    """
    path = tmp_path / "model.py"
    path.write_text(
        "class First:\n    def build(self):\n        return 1\n"
        "class Second:\n    def build(self):\n        return 2\n",
    )
    before = Symbols(tmp_path, {"gana": tmp_path})
    first = before.describe((str(path), 2, "build"))
    second = before.describe((str(path), 5, "build"))
    CHECK.assertNotEqual(first["id"], second["id"])
    path.write_text("# shifted\n" + path.read_text())
    after = Symbols(tmp_path, {"gana": tmp_path})
    CHECK.assertEqual(
        first["id"],
        after.describe((str(path), 3, "build"))["id"],
    )


def test_nested_decorated_names(tmp_path):
    """Decorator entry lines resolve to the decorated qualified function."""
    path = tmp_path / "sample.py"
    path.write_text(
        "class C:\n    @staticmethod\n    def run():\n"
        "        def nested():\n            return 1\n"
        "        return nested()\n",
    )
    names = named_functions(path)
    CHECK.assertEqual(names[2], "C.run")
    CHECK.assertEqual(names[4], "C.run.nested")


def test_raw_stats_preserve_callers(tmp_path):
    """
    Caller edges and recursive counters are not confused with total calls.
    """
    path = tmp_path / "sample.py"
    path.write_text(
        "def outer():\n    return inner()\ndef inner():\n    return 1\n",
    )
    outer, inner = (str(path), 1, "outer"), (str(path), 3, "inner")
    stats = {inner: (2, 3, 0.4, 0.6, {outer: (3, 2, 0.4, 0.6)})}
    row = function_rows(stats, Symbols(tmp_path, {"gana": tmp_path}))[0]
    CHECK.assertEqual(row["primitive_calls"], 2)
    CHECK.assertEqual(row["calls"], 3)
    CHECK.assertEqual(row["callers"][0]["id"], "gana/sample.py::outer")
    CHECK.assertEqual(row["callers"][0]["calls"], 3)
    CHECK.assertEqual(row["callers"][0]["primitive_calls"], 2)


def test_recursive_cprofile_counters(profiled_project):
    """Validate counter ordering against real recursive profiler output."""
    # A child session avoids nesting cProfile instances, which Python rejects.
    pytester, root = profiled_project
    (root / "src/toy/__init__.py").write_text(
        "def step(depth):\n"
        "    return step(depth - 1) if depth else 1\n"
        "def work():\n    return step(3)\n",
    )
    output = root / "recursive"
    CHECK.assertEqual(invoke_pytest(pytester, output).ret, 0)
    rows = read_json(output / "profile.json")["functions"]
    row = next(row for row in rows if row["id"] == "toy/__init__.py::step")
    CHECK.assertEqual((row["calls"], row["primitive_calls"]), (4, 1))
    caller = next(c for c in row["callers"] if c["id"] == row["id"])
    CHECK.assertEqual((caller["calls"], caller["primitive_calls"]), (3, 1))


def test_history_selects_matching_existing_report(tmp_path):
    """Skip broken/mismatched pointers and retain their diagnostic messages."""
    report = tmp_path / "profile.json"
    write_json(report, recorded_report())
    write_json(
        tmp_path / "run-1.json",
        {"fingerprint": "match", "report": str(report)},
    )
    write_json(
        tmp_path / "run-2.json",
        {"fingerprint": "different", "report": str(report)},
    )
    (tmp_path / "run-3.json").write_text("broken json")
    selected, errors = prior_report(tmp_path, {"fingerprint": "match"})
    CHECK.assertEqual(selected, report)
    CHECK.assertEqual(len(errors), 1)


def test_hashes_detect_changed_inputs(tmp_path):
    """Hash exact bytes while making mapping order irrelevant."""
    path = tmp_path / "data.csv"
    path.write_text("1,2\n")
    before = file_hashes({"data": path})
    path.write_text("1,3\n")
    CHECK.assertNotEqual(before, file_hashes({"data": path}))
    CHECK.assertEqual(
        fingerprint({"a": 1, "b": 2}),
        fingerprint({"b": 2, "a": 1}),
    )


def sandbox_project(tmp_path):
    """
    Prepare a tiny independently runnable checkout using the actual hooks.
    """
    for directory in ("tools", "tests", "src/toy"):
        (tmp_path / directory).mkdir(parents=True)
    for name in (
        "profile_stats.py",
        "profile_context.py",
        "pytest_profile.py",
    ):
        (tmp_path / "tools" / name).write_bytes(
            (ROOT / "tools" / name).read_bytes(),
        )
    (tmp_path / "conftest.py").write_bytes((ROOT / "conftest.py").read_bytes())
    (tmp_path / "src/toy/__init__.py").write_text(
        "def step():\n    return 1\ndef work():\n    return step()\n",
    )
    (tmp_path / "tests/test_sample.py").write_text(
        "from toy import work\ndef test_work():\n    assert work() > 0\n",
    )
    return tmp_path


@pytest.fixture
def profiled_project(pytester, monkeypatch):
    """Use pytest's own isolated process fixture with controlled inputs."""
    root = sandbox_project(pytester.path)
    settings = {
        "PYTHONPATH": str(root / "src") + os.pathsep + str(root),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTEST_FUNCTION_PROFILE_HISTORY": str(root / "history"),
    }
    for name, value in settings.items():
        monkeypatch.setenv(name, value)
    for name in (
        "PYTEST_ADDOPTS",
        "PYTEST_PLUGINS",
        "PYTEST_FUNCTION_PROFILE_OUTPUT",
    ):
        monkeypatch.delenv(name, raising=False)
    return pytester, root


def invoke_pytest(pytester, output):
    """Exercise the real pytest entry point using its subprocess test API."""
    return pytester.runpytest_subprocess(
        "tests",
        "-q",
        "--function-profile-output",
        str(output),
        timeout=60,
    )


def test_direct_pytest_profiles_and_compares_code_changes(profiled_project):
    """Every direct invocation records profiles and attributes extra calls."""
    pytester, root = profiled_project
    first, second = root / "first", root / "second"
    CHECK.assertEqual(invoke_pytest(pytester, first).ret, 0)
    (root / "src/toy/__init__.py").write_text(
        "# moved line\ndef step():\n    return 1\ndef work():\n"
        "    return sum(step() for _ in range(3))\n",
    )
    CHECK.assertEqual(invoke_pytest(pytester, second).ret, 0)
    comparison = read_json(second / "comparison.json")
    CHECK.assertEqual(comparison["status"], "comparable")
    rows = {r["id"]: r for r in comparison["functions"]}
    CHECK.assertEqual(rows["toy/__init__.py::step"]["calls"]["delta"], 2)
    CHECK.assertTrue((second / "profile.pstats").stat().st_size)
    CHECK.assertIn(
        "Project functions by self time",
        (second / "profile.txt").read_text(),
    )


@pytest.mark.parametrize("failure", ["assertion", "collection"])
def test_failures_keep_profiles_and_failing_exit(profiled_project, failure):
    """Assertion and collection failures must not lose their true exit code."""
    pytester, root = profiled_project
    code = (
        "def test_failure():\n    assert False\n"
        if failure == "assertion"
        else "invalid syntax !!!"
    )
    (root / "tests/test_sample.py").write_text(code)
    output = root / "failed"
    result = invoke_pytest(pytester, output)
    CHECK.assertNotEqual(result.ret, 0)
    report = read_json(output / "profile.json")
    CHECK.assertEqual(report["exit_code"], result.ret)
    CHECK.assertFalse(report["eligible"])
    CHECK.assertTrue((output / "profile.pstats").exists())
    CHECK.assertFalse(list((root / "history").glob("run-*.json")))


def test_existing_profile_is_never_overwritten(profiled_project):
    """An explicitly reused output path fails while preserving old evidence."""
    pytester, root = profiled_project
    output = root / "existing"
    output.mkdir()
    sentinel = output / "profile.json"
    sentinel.write_text("keep this report")
    CHECK.assertNotEqual(invoke_pytest(pytester, output).ret, 0)
    CHECK.assertEqual(sentinel.read_text(), "keep this report")
