"""Portable cProfile reports and comparisons for the repository test runners.

Cumulative times overlap through the call tree. Use exclusive/self time to
attribute added time; these instrumented measurements are diagnostic only.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA = 1
Row = dict[str, Any]


def read_json(path: Path) -> Any:
    """Read one explicit report or history entry without executing it."""
    return json.loads(path.read_text())


def write_json(path: Path, value: Any) -> None:
    """Write a complete structured artifact into a fresh run directory."""
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def fingerprint(value: Any) -> str:
    """Identify comparison inputs independently of mapping insertion order."""
    data = json.dumps(value, sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()


def file_hashes(paths: dict[str, Path]) -> dict[str, str]:
    """Hash source and workload inputs without retaining their contents."""
    return {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in sorted(paths.items())
    }


def named_functions(path: Path) -> dict[int, str]:
    """Resolve methods and nested functions across line-number-only edits."""
    result: dict[int, str] = {}
    pending: list[tuple[str, ast.AST]] = [("", ast.parse(path.read_text()))]
    while pending:
        prefix, node = pending.pop()
        for child in getattr(node, "body", ()):
            if isinstance(
                child,
                (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                name = prefix + child.name
                first = min(
                    [child.lineno, *[d.lineno for d in child.decorator_list]],
                )
                result.update(
                    (line, name) for line in range(first, child.lineno + 1)
                )
                pending.append((name + ".", child))
    return result


class Symbols:
    """Normalize project paths and cache qualified function-name lookup."""

    def __init__(self, root: Path, packages: dict[str, Path]):
        """Use actual loaded package paths, including local dependencies."""
        self.root = root.resolve()
        self.packages = packages
        self.names: dict[Path, dict[int, str]] = {}

    def location(self, filename: str) -> tuple[str, bool]:
        """
        Keep project, standard-library and dependency paths distinguishable.
        """
        if filename.startswith(("~", "<")):
            return filename, False
        path = Path(filename).resolve()
        for package, directory in self.packages.items():
            if path.is_relative_to(directory):
                return f"{package}/{path.relative_to(directory)}", True
        if path.is_relative_to(self.root):
            return str(path.relative_to(self.root)), False
        if "site-packages" in path.parts:
            return "site-packages/" + str(path).split("site-packages/", 1)[
                1
            ], False
        prefix = Path(sys.base_prefix).resolve()
        if path.is_relative_to(prefix):
            return "python/" + str(path.relative_to(prefix)), False
        return filename, False

    def describe(self, key: tuple[str, int, str]) -> Row:
        """
        Use qualified names for project functions, preserving display lines.
        """
        filename, line, name = key
        location, project = self.location(filename)
        if project:
            path = Path(filename)
            if path not in self.names:
                self.names[path] = named_functions(path)
            name = self.names[path].get(line, f"{name}@{line}")
        else:
            name = f"{name}@{line}"
        return {
            "id": f"{location}::{name}",
            "file": location,
            "line": line,
            "function": name,
            "project": project,
        }


def function_rows(stats: dict, symbols: Symbols) -> list[Row]:
    """Retain exact cProfile counters plus caller edges for diagnosis."""
    rows = []
    for key, (primitive, calls, own, cumulative, callers) in stats.items():
        row = symbols.describe(key)
        row.update(
            primitive_calls=primitive,
            calls=calls,
            self_seconds=own,
            cumulative_seconds=cumulative,
        )
        row["callers"] = [
            {
                **symbols.describe(caller),
                # cProfile caller edges store total calls before primitives;
                # the containing function tuple uses the opposite order.
                "primitive_calls": values[1],
                "calls": values[0],
                "self_seconds": values[2],
                "cumulative_seconds": values[3],
            }
            for caller, values in callers.items()
        ]
        rows.append(row)
    return sorted(rows, key=lambda row: (-row["self_seconds"], row["id"]))


def aggregated(rows: list[Row]) -> dict[str, Row]:
    """
    Combine duplicate code objects that resolve to one stable function ID.
    """
    result: dict[str, Row] = {}
    for row in rows:
        current = result.setdefault(
            row["id"],
            {
                "id": row["id"],
                "project": row["project"],
                "calls": 0,
                "self_seconds": 0.0,
                "cumulative_seconds": 0.0,
            },
        )
        for field in ("calls", "self_seconds", "cumulative_seconds"):
            current[field] += row[field]
    return result


def function_delta(key: str, before: Row, after: Row) -> Row:
    """Separate more calls from increased measured cost per call."""
    result: Row = {
        "id": key,
        "project": after.get("project", before.get("project")),
    }
    for field in ("calls", "self_seconds", "cumulative_seconds"):
        old, new = before.get(field, 0), after.get(field, 0)
        result[field] = {"before": old, "after": new, "delta": new - old}
    result["self_seconds_per_call"] = {
        "before": (
            before.get("self_seconds", 0) / before["calls"]
            if before.get("calls")
            else None
        ),
        "after": (
            after.get("self_seconds", 0) / after["calls"]
            if after.get("calls")
            else None
        ),
    }
    return result


def compare_reports(before: Row, after: Row) -> Row:
    """Refuse time deltas when workload, host or instrumentation differs."""
    keys = set(before["comparison_inputs"]) | set(after["comparison_inputs"])
    changed = sorted(
        k
        for k in keys
        if before["comparison_inputs"].get(k)
        != after["comparison_inputs"].get(k)
    )
    if changed:
        return {"status": "incompatible", "changed_inputs": changed}
    if not before["eligible"] or not after["eligible"]:
        return {
            "status": "incomplete",
            "reason": "Failed, empty or changing-source test run",
        }
    left, right = (
        aggregated(before["functions"]),
        aggregated(after["functions"]),
    )
    rows = [
        function_delta(k, left.get(k, {}), right.get(k, {}))
        for k in left.keys() | right.keys()
    ]
    rows.sort(key=lambda row: (-row["self_seconds"]["delta"], row["id"]))
    return {
        "status": "comparable",
        "functions": rows,
        "note": (
            "Instrumented diagnostic deltas, not benchmark speed claims. "
            "Cumulative times overlap."
        ),
    }


def prior_report(history: Path, current: Row) -> tuple[Path | None, list[str]]:
    """
    Choose the newest matching completed run without promoting a baseline.
    """
    skipped: list[str] = []
    for path in sorted(history.glob("run-*.json"), reverse=True):
        try:
            pointer = read_json(path)
            candidate = Path(pointer["report"])
            if (
                pointer["fingerprint"] == current["fingerprint"]
                and candidate.is_file()
            ):
                return candidate, skipped
        except (OSError, ValueError, KeyError) as error:
            skipped.append(f"{path.name}: {error}")
    return None, skipped


def comparison_for(report: Row, history: Path, reference: Path | None) -> Row:
    """Honor an explicit reference or find a compatible local history entry."""
    skipped: list[str] = []
    if reference is None:
        reference, skipped = prior_report(history, report)
    if reference is None:
        return {"status": "no_compatible_reference", "history_errors": skipped}
    if reference.is_dir():
        reference = reference / "profile.json"
    comparison = compare_reports(read_json(reference), report)
    comparison.update(reference=str(reference), history_errors=skipped)
    return comparison


def table(rows: list[Row], field: str, limit: int = 20) -> list[str]:
    """Rank functions by exclusive or cumulative seconds, with call counts."""
    ordered = sorted(rows, key=lambda row: (-row[field], row["id"]))[:limit]
    return [
        f"{row[field]:10.6f}s {row['calls']:10d} calls  {row['id']}"
        for row in ordered
    ]


def comparison_text(comparison: Row) -> list[str]:
    """
    Show positive project self-time deltas without summing cumulative time.
    """
    if comparison["status"] != "comparable":
        return ["Comparison: " + json.dumps(comparison, sort_keys=True)]
    rows = [
        r
        for r in comparison["functions"]
        if r["project"] and r["self_seconds"]["delta"] > 0
    ]
    return [
        "Largest project self-time increases:",
        *[
            f"{r['self_seconds']['delta']:+.6f}s  "
            f"{r['calls']['delta']:+d} calls  {r['id']}"
            for r in rows[:20]
        ],
    ]


def report_text(report: Row, comparison: Row) -> str:
    """Explain timing scope beside both project and process-wide hot spots."""
    project = [r for r in report["functions"] if r["project"]]
    lines = [
        "Automatic cProfile test diagnostics",
        report["scope"],
        "Self = time inside a function; cumulative = time including callees.",
        "Cumulative rows overlap. Coverage/profiling overhead is included.",
        "These are diagnostic timings, not uninstrumented benchmarks.",
        "Anonymous expressions use line-based IDs; moved lines can appear",
        "as added/removed expressions. Compare their named callers too.",
        "",
        "Project functions by self time:",
        *table(project, "self_seconds"),
        "",
        "Project functions by cumulative time:",
        *table(project, "cumulative_seconds"),
        "",
        "All functions by self time:",
        *table(report["functions"], "self_seconds"),
        "",
        *comparison_text(comparison),
    ]
    return "\n".join(lines) + "\n"


def save_report(
    output: Path,
    history: Path,
    report: Row,
    reference: Path | None,
) -> Row:
    """
    Save the immutable report before appending its eligible history entry.
    """
    comparison = comparison_for(report, history, reference)
    write_json(output / "profile.json", report)
    write_json(output / "comparison.json", comparison)
    (output / "profile.txt").write_text(report_text(report, comparison))
    if report["eligible"]:
        history.mkdir(parents=True, exist_ok=True)
        write_json(
            history / f"run-{report['run_id']}.json",
            {
                "report": str(output / "profile.json"),
                "fingerprint": report["fingerprint"],
            },
        )
    return comparison
