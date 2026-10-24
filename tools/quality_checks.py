"""Small, testable checks for coverage floors and exact Radon A/B limits."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any


def coverage_percentages(totals: dict[str, Any]) -> tuple[float, float]:
    """
    Compute separate statement/branch percentages; reject empty measurement.
    """
    statements = int(totals["num_statements"])
    branches = int(totals["num_branches"])
    if statements < 1:
        message = "Coverage contains no measured statements."
        raise ValueError(message)
    statement_percent = 100 * int(totals["covered_lines"]) / statements
    branch_percent = (
        100 * int(totals["covered_branches"]) / branches if branches else 100.0
    )
    return statement_percent, branch_percent


def coverage_failures(
    totals: dict[str, Any],
    statement_floor: float,
    branch_floor: float,
) -> list[str]:
    """Fail either independent floor rather than using blended coverage."""
    measured = coverage_percentages(totals)
    floors = (statement_floor, branch_floor)
    names = ("statements", "branches")
    return [
        f"{name}: {value:.3f}% < {floor:.3f}%"
        for name, value, floor in zip(names, measured, floors)
        if value < floor
    ]


def radon_blocks(entries: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    """Include methods and nested closures, not only top-level functions."""
    for block in entries:
        yield block
        yield from radon_blocks(block.get("methods", []))
        yield from radon_blocks(block.get("closures", []))


def complexity_failures(report: dict[str, Any]) -> list[str]:
    """Reject unreadable Radon files and every block outside grades A/B."""
    failures = []
    for filename, entries in report.items():
        if not isinstance(entries, list):
            failures.append(f"{filename}: Radon could not analyze the file")
            continue
        for block in radon_blocks(entries):
            if block["rank"] not in ("A", "B"):
                failures.append(
                    f"{filename}:{block['lineno']} {block['name']}: "
                    f"{block['rank']}",
                )
    return failures
