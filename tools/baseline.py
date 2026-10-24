"""Run Gana's quality baseline in an isolated working directory.

Usage: .venv/bin/python tools/baseline.py [--output quality/runs/run-name]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import NoReturn
from xml.parsers import expat

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements/baseline-macos-x86_64-py313.lock"
SEED = "20260921"
METRIC_GROUP_COUNT = 3


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_files():
    """Include the automatic pytest hook in each measured source snapshot."""
    files = [
        p
        for folder in ("src", "tests", "tools")
        for p in (ROOT / folder).rglob("*.py")
    ]
    files += [
        ROOT / "pyproject.toml",
        ROOT / "tox.ini",
        ROOT / ".python-version",
        ROOT / "conftest.py",
        LOCK,
    ]
    return sorted(files)


def source_hashes():
    return {
        str(p.relative_to(ROOT)): digest(p.read_bytes())
        for p in source_files()
    }


def git(*args):
    """Run internal provenance queries through an absolute Git executable."""
    executable = shutil.which("git")
    if executable is None:
        message = "Git is required to record baseline provenance."
        raise FileNotFoundError(message)
    command = [str(Path(executable).resolve()), *args]
    # Reviewed: internal read-only Git arguments, passed separately, no shell.
    return subprocess.check_output(  # noqa: S603
        command,
        cwd=ROOT,
        text=True,
        shell=False,
    ).strip()


def check_environment():
    expected = dict(
        re.findall(r"^([\w.-]+)==([^\s\\]+)", LOCK.read_text(), re.M),
    )
    actual = {
        re.sub(r"[-_.]+", "-", d.metadata["Name"]).lower(): d.version
        for d in metadata.distributions()
    }
    problems = [
        f"{name}: expected {version}, found {actual.get(name, 'missing')}"
        for name, version in expected.items()
        if actual.get(name) != version
    ]
    extras = sorted(set(actual) - set(expected))
    if extras:
        problems.append("Unexpected distributions: " + ", ".join(extras))
    if platform.python_version() != "3.13.7":
        problems.append("The reference baseline requires Python 3.13.7.")
    if sys.platform != "darwin" or platform.machine() != "x86_64":
        problems.append(
            "This lock targets macOS x86_64; "
            "create a separate lock for other platforms.",
        )
    if problems:
        raise SystemExit(
            "Baseline environment does not match:\n" + "\n".join(problems),
        )
    return actual


def run_command(name, args, work, env, output):
    """Retain output and exit status even when a baseline check fails."""
    command = [sys.executable, "-B", "-m", *args]
    print(f"Running {name}...", flush=True)
    try:
        # Reviewed: current Python runs internally selected quality modules.
        result = subprocess.run(  # noqa: S603
            command,
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
            shell=False,
        )
        stdout, stderr, code = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        stdout, stderr, code = (
            "",
            "Command exceeded the 600-second timeout.\n",
            124,
        )
    (output / f"{name}.stdout.txt").write_text(stdout)
    (output / f"{name}.stderr.txt").write_text(stderr)
    return {"command": command, "exit_code": code}, stdout


def metric_summary(metrics):
    """
    Summarize measured complexity, maintainability, and integer raw counts.
    """
    blocks = [
        (path, block)
        for path, entries in metrics["complexity"].items()
        for block in entries
    ]
    ranks = Counter(block["rank"] for _, block in blocks)
    raw: Counter[str] = Counter()
    for values in metrics["raw"].values():
        raw.update(values)
    return {
        "complexity": {
            "blocks": len(blocks),
            "grades": dict(sorted(ranks.items())),
            "average": sum(b["complexity"] for _, b in blocks) / len(blocks),
            "hotspots": [
                {
                    "file": p,
                    "name": b["name"],
                    "line": b["lineno"],
                    "score": b["complexity"],
                    "grade": b["rank"],
                }
                for p, b in sorted(
                    blocks,
                    key=lambda x: (-x[1]["complexity"], x[0], x[1]["lineno"]),
                )[:10]
            ],
        },
        "maintainability": metrics["maintainability"],
        "raw": dict(raw),
    }


def _reject_xml_declaration(*_args: object) -> NoReturn:
    """Reject DTDs and entities before any expansion or external lookup."""
    message = "DTD and entity declarations are not allowed in JUnit XML."
    raise ValueError(message)


def _junit_counts(path: Path) -> dict[str, int]:
    """Stream local JUnit counts without DTDs or entity reconstruction.

    Keep the reference environment standard-library-only. Expat handles XML
    encodings; callbacks reject declarations rather than scanning raw bytes.
    Namespace-expanded names retain the prior bare-testsuite selection rule.
    """
    counts: Counter[str] = Counter()

    def record(name: str, attributes: dict[str, str]) -> None:
        """Accumulate the same four counters for each unqualified suite."""
        if name == "testsuite":
            for key in ("tests", "failures", "errors", "skipped"):
                counts[key] += int(attributes.get(key, 0))

    parser = expat.ParserCreate(namespace_separator="}")
    parser.StartElementHandler = record
    parser.StartDoctypeDeclHandler = _reject_xml_declaration
    parser.EntityDeclHandler = _reject_xml_declaration
    parser.ExternalEntityRefHandler = _reject_xml_declaration
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    with path.open("rb") as stream:
        parser.ParseFile(stream)
    return dict(counts)


def test_summary(output):
    """Read retained JUnit counts and coverage without rerunning tests."""
    summary = {}
    junit = output / "pytest.xml"
    if junit.exists():
        summary["tests"] = _junit_counts(junit)
    coverage = output / "coverage.json"
    if coverage.exists():
        report = json.loads(coverage.read_text())
        summary["coverage"] = report["totals"]
        summary["coverage_by_file"] = {
            str(Path(path).relative_to(ROOT)): entry["summary"]
            for path, entry in report["files"].items()
        }
    return summary


def compare(reference, output, before, summary):
    old = json.loads((reference / "summary.json").read_text())
    old_inputs = json.loads((reference / "source-hashes.json").read_text())
    old_manifest = json.loads((reference / "manifest.json").read_text())
    current_manifest = json.loads((output / "manifest.json").read_text())
    environment_fields = (
        "python",
        "platform",
        "machine",
        "packages",
        "seed",
        "environment",
    )
    comparison = {
        "same_source": old_inputs == before,
        "same_environment": all(
            old_manifest[k] == current_manifest[k] for k in environment_fields
        ),
        "same_metrics": old == summary,
        "reference": str(reference),
    }
    write_json(output / "comparison.json", comparison)
    print(json.dumps(comparison, indent=2))
    return all(
        comparison[k]
        for k in ("same_source", "same_environment", "same_metrics")
    )


def snapshot_source(output):
    """Retain hashes, local diff and source before any measurement runs."""
    before = source_hashes()
    write_json(output / "source-hashes.json", before)
    (output / "source.patch").write_text(
        git("diff", "--binary", "HEAD", "--", "src", "tests", "pyproject.toml")
        + "\n",
    )
    with tarfile.open(output / "source.tar.gz", "w:gz") as archive:
        for path in source_files():
            archive.add(path, arcname=str(path.relative_to(ROOT)))
    return before


def deterministic_environment():
    """Fix process settings shared by the manifest and child commands."""
    return {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "MPLBACKEND": "Agg",
        "LC_ALL": "C",
        "LANG": "C",
        "TZ": "UTC",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMBA_NUM_THREADS": "1",
    }


def collect_metrics(work, env, output, commands):
    """Retain each metric and its status, continuing after failed commands."""
    metrics = {}
    for name, command in (
        ("complexity", "cc"),
        ("maintainability", "mi"),
        ("raw", "raw"),
    ):
        result, stdout = run_command(
            name,
            ["radon", command, str(ROOT / "src/gana"), "-j"],
            work,
            env,
            output,
        )
        commands[name] = result
        if result["exit_code"] == 0:
            metrics[name] = {
                str(Path(k).relative_to(ROOT)): v
                for k, v in json.loads(stdout).items()
            }
            write_json(output / f"{name}.json", metrics[name])
    result, _ = run_command(
        "complexity-b-or-worse",
        ["radon", "cc", str(ROOT / "src/gana"), "--min", "B", "-s", "-a"],
        work,
        env,
        output,
    )
    commands["complexity-b-or-worse"] = result
    return metrics


def baseline_test_arguments(output):
    """Keep the reference test workload, plugins, seed and artifact paths."""
    return [
        "pytest",
        str(ROOT / "tests"),
        "-q",
        "-c",
        str(ROOT / "pyproject.toml"),
        "-p",
        "no:cacheprovider",
        "-p",
        "pytest_cov",
        "-p",
        "hypothesis.extra.pytestplugin",
        "--tb=short",
        f"--hypothesis-seed={SEED}",
        f"--cov={ROOT / 'src/gana'}",
        f"--cov-config={ROOT / 'pyproject.toml'}",
        "--cov-branch",
        "--cov-report=term-missing",
        f"--cov-report=json:{output / 'coverage.json'}",
        f"--junitxml={output / 'pytest.xml'}",
    ]


def run_measurements(output, environment, manifest):
    """Run checks in scratch space and retain test function profiles."""
    metrics = {}
    with tempfile.TemporaryDirectory(prefix="gana-baseline-") as scratch:
        work = Path(scratch)
        # Both legacy src.gana imports and current gana imports must resolve
        # to this checkout when tests run from the isolated working directory.
        env = {
            **os.environ,
            **environment,
            "PYTHONPATH": os.pathsep.join((str(ROOT), str(ROOT / "src"))),
            "MPLCONFIGDIR": str(work / "matplotlib"),
            "HYPOTHESIS_STORAGE_DIRECTORY": str(work / "hypothesis"),
            "COVERAGE_FILE": str(output / ".coverage"),
            "PYTEST_FUNCTION_PROFILE_OUTPUT": str(output / "profile"),
        }
        for inherited in (
            "PYTEST_ADDOPTS",
            "COVERAGE_PROCESS_START",
            "COVERAGE_RCFILE",
        ):
            env.pop(inherited, None)
        metrics = collect_metrics(work, env, output, manifest["commands"])
        test_args = baseline_test_arguments(output)
        result, _ = run_command("pytest", test_args, work, env, output)
        manifest["commands"]["pytest"] = result
    return metrics


def main():
    """Coordinate a reproducible run and fail on changed inputs or checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--compare",
        type=Path,
        help=(
            "Fail if source, environment, or measured summary "
            "differs from a prior run"
        ),
    )
    args = parser.parse_args()
    packages = check_environment()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = (args.output or ROOT / "quality/runs" / stamp).resolve()
    output.mkdir(parents=True, exist_ok=False)
    before = snapshot_source(output)
    environment = deterministic_environment()
    manifest = {
        "created_utc": stamp,
        "git_commit": git("rev-parse", "HEAD"),
        "git_branch": git("branch", "--show-current"),
        "git_status": git("status", "--short"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "interpreter": sys.executable,
        "packages": packages,
        "seed": SEED,
        "environment": environment,
        "lock_sha256": digest(LOCK.read_bytes()),
        "source_sha256": digest(json.dumps(before, sort_keys=True).encode()),
        "commands": {},
    }
    write_json(output / "manifest.json", manifest)
    metrics = run_measurements(output, environment, manifest)
    unchanged = before == source_hashes()
    manifest["source_unchanged"] = unchanged
    write_json(output / "manifest.json", manifest)
    summary = (
        metric_summary(metrics) if len(metrics) == METRIC_GROUP_COUNT else {}
    )
    summary.update(test_summary(output))
    write_json(output / "summary.json", summary)
    success = unchanged and all(
        c["exit_code"] == 0 for c in manifest["commands"].values()
    )
    if args.compare:
        success = (
            compare(args.compare.resolve(), output, before, summary)
            and success
        )
    print(f"Baseline {'passed' if success else 'FAILED'}. Reports: {output}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
