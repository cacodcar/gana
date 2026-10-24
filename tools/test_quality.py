"""Regression tests for false-success cases in the quality gate machinery."""

import pytest

import quality
from quality_checks import (
    complexity_failures,
    coverage_failures,
    coverage_percentages,
)


def test_branch_failure_is_not_hidden_by_statement_coverage():
    """Perfect statement coverage must not conceal a missing branch."""
    totals = {
        "num_statements": 10,
        "covered_lines": 10,
        "num_branches": 4,
        "covered_branches": 3,
    }
    if coverage_failures(totals, 90, 80) != ["branches: 75.000% < 80.000%"]:
        pytest.fail("The independent branch coverage gate did not fail.")


def test_empty_coverage_is_rejected():
    """A source-discovery failure cannot report a vacuous coverage success."""
    with pytest.raises(ValueError, match="no measured statements"):
        coverage_percentages({"num_statements": 0, "num_branches": 0})


def test_floor_boundary_and_branchless_module():
    """Exact floor values pass, including a module with no control branches."""
    totals = {
        "num_statements": 10,
        "covered_lines": 9,
        "num_branches": 0,
        "covered_branches": 0,
    }
    if coverage_failures(totals, 90, 100):
        pytest.fail("An exact floor boundary should pass.")


def test_nested_complexity_is_enforced():
    """A complex method inside a low-complexity class must fail the gate."""
    report = {
        "example.py": [
            {
                "rank": "A",
                "name": "Example",
                "lineno": 1,
                "methods": [{"rank": "C", "name": "nested", "lineno": 2}],
            },
        ],
    }
    if complexity_failures(report) != ["example.py:2 nested: C"]:
        pytest.fail("Nested complexity was not checked.")


def test_unreadable_complexity_report_fails():
    """Radon error payloads cannot be mistaken for an empty passing file."""
    if not complexity_failures({"invalid.py": {"error": "syntax error"}}):
        pytest.fail("A Radon parse error should fail.")


def test_documentation_generation_cannot_overwrite_sources(
    tmp_path,
    monkeypatch,
):
    """Autosummary may replace pages only inside the disposable docs copy."""
    root = tmp_path / "project"
    docs = root / "docs"
    docs.mkdir(parents=True)
    original = docs / "api.rst"
    original.write_text("user-authored API page")
    for name in ("README.md", "CHANGELOG.md", "LICENSE", "pyproject.toml"):
        (root / name).write_text(name)
    monkeypatch.setattr(quality, "ROOT", root)
    work = tmp_path / "work"
    work.mkdir()
    arguments = ["-m", "sphinx", str(docs), str(tmp_path / "html")]
    copied = work / "documentation" / "docs"
    actual = quality.isolated_documentation(work, arguments)
    if actual != ["-m", "sphinx", str(copied), str(tmp_path / "html")]:
        pytest.fail(f"Unexpected isolated build arguments: {actual!r}")
    (copied / "api.rst").write_text("generated replacement")
    if original.read_text() != "user-authored API page":
        pytest.fail("The documentation build overwrote a checkout source.")
    if (copied.parent / "README.md").read_text() != "README.md":
        pytest.fail("Root-level include targets were not preserved.")
