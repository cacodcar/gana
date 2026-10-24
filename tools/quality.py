"""Run blocking quality checks without creating solver outputs in the checkout.

Each invocation preserves commands, exit codes, versions and source hashes in
an independently named report directory. Use --baseline to require the recorded
hash-locked environment before running all gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import tomllib
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

from quality_checks import complexity_failures, coverage_failures

ROOT = Path(__file__).resolve().parents[1]
CHECKS = (
    "tests",
    "complexity",
    "maintainability",
    "raw",
    "lint",
    "format",
    "types",
    "docs",
    "dependencies",
)


def settings() -> dict[str, Any]:
    """
    Read package-specific floors from the versioned quality configuration.
    """
    with (ROOT / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)["tool"]["research-quality"]


def write_json(path: Path, value: Any) -> None:
    """Write readable measurement data; callers choose a fresh directory."""
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def source_hashes() -> dict[str, str]:
    """
    Identify measured source, tooling and gate configuration before/after.
    """
    paths: list[Path] = []
    for directory in (
        "src",
        "tests",
        "tools",
        "docs",
        "requirements",
        ".github",
        ".githooks",
        "crates",
    ):
        paths.extend(p for p in (ROOT / directory).rglob("*") if p.is_file())
    paths.extend(
        ROOT / name
        for name in (
            "pyproject.toml",
            "ruff.toml",
            "tox.ini",
            ".coveragerc",
            "conftest.py",
            "Cargo.toml",
            "Cargo.lock",
            "README.md",
            "CHANGELOG.md",
            "LICENSE",
        )
    )
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(
            path.read_bytes(),
        ).hexdigest()
        for path in sorted(paths)
        if path.exists() and "__pycache__" not in path.parts
    }


def test_environment(work: Path, output: Path) -> dict[str, str]:
    """Fix numerical randomness and redirect solver, plot and test caches."""
    env = dict(os.environ)
    env.update(
        {
            "PYTHONPATH": os.pathsep.join((str(ROOT), str(ROOT / "src"))),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "LC_ALL": "C",
            "LANG": "C",
            "TZ": "UTC",
            "MPLBACKEND": "Agg",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "MPLCONFIGDIR": str(work / "matplotlib"),
            "HYPOTHESIS_STORAGE_DIRECTORY": str(work / "hypothesis"),
            "COVERAGE_FILE": str(output / ".coverage"),
            "PYTEST_FUNCTION_PROFILE_OUTPUT": str(output / "profile"),
            "RUFF_CACHE_DIR": str(work / "ruff"),
        },
    )
    return env


def run_process(
    name: str,
    arguments: list[str],
    work: Path,
    env: dict[str, str],
    output: Path,
    *,
    executable: str | None = sys.executable,
) -> dict[str, Any]:
    """
    Capture a check's status and streams; None runs a native argv directly.
    """
    command = [executable, *arguments] if executable else arguments
    try:
        # Reviewed: internally assembled check commands, never a shell string.
        result = subprocess.run(  # noqa: S603
            command,
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
            shell=False,
        )
        stdout, stderr, code = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        stdout, stderr, code = (
            "",
            "Quality command exceeded 900 seconds.\n",
            124,
        )
    (output / f"{name}.stdout.txt").write_text(stdout)
    (output / f"{name}.stderr.txt").write_text(stderr)
    print(f"{name}: exit {code}", flush=True)
    return {"command": command, "exit_code": code}


def test_arguments(config: dict[str, Any], output: Path) -> list[str]:
    """
    Run package and tooling tests with separately reported branch coverage.
    """
    return [
        "-m",
        "pytest",
        str(ROOT / "tests"),
        str(ROOT / "tools"),
        "-c",
        str(ROOT / "pyproject.toml"),
        "-p",
        "no:cacheprovider",
        "-q",
        "--hypothesis-seed=20260928",
        f"--cov={ROOT / 'src' / config['package']}",
        f"--cov-config={ROOT / '.coveragerc'}",
        "--cov-branch",
        "--cov-report=term-missing",
        f"--cov-report=json:{output / 'coverage.json'}",
        f"--cov-report=xml:{output / 'coverage.xml'}",
        f"--junitxml={output / 'pytest.xml'}",
    ]


def check_commands(
    config: dict[str, Any],
    output: Path,
) -> dict[str, list[str]]:
    """
    Use the same explicit sources and configuration in tasks, hooks and CI.
    """
    sources = [
        str(ROOT / "src"),
        str(ROOT / "tests"),
        str(ROOT / "tools"),
        str(ROOT / "conftest.py"),
    ]
    return {
        "tests": test_arguments(config, output),
        "complexity": [
            "-m",
            "radon",
            "cc",
            str(ROOT / "src"),
            str(ROOT / "tools"),
            "-j",
        ],
        "maintainability": [
            "-m",
            "radon",
            "mi",
            str(ROOT / "src"),
            str(ROOT / "tools"),
            "-s",
        ],
        "raw": [
            "-m",
            "radon",
            "raw",
            str(ROOT / "src"),
            str(ROOT / "tools"),
            str(ROOT / "conftest.py"),
        ],
        "lint": [
            "-m",
            "ruff",
            "check",
            "--config",
            str(ROOT / "ruff.toml"),
            *sources,
        ],
        # The runner uses a temporary cwd, so pass the repository policy.
        "flake8": [
            "-m",
            "flake8",
            "--config",
            str(ROOT / "tox.ini"),
            *sources,
        ],
        "format": [
            "-m",
            "ruff",
            "format",
            "--check",
            "--config",
            str(ROOT / "ruff.toml"),
            *sources,
        ],
        "types": [
            "-m",
            "mypy",
            "--config-file",
            str(ROOT / "pyproject.toml"),
            str(ROOT / "src"),
            str(ROOT / "tools"),
        ],
        "docs": [
            "-m",
            "sphinx",
            "-W",
            "--keep-going",
            "-b",
            "html",
            "-D",
            "nb_execution_mode=off",
            str(ROOT / "docs"),
            str(output / "html"),
        ],
        "dependencies": ["-m", "pip", "check"],
    }


def isolated_documentation(work: Path, arguments: list[str]) -> list[str]:
    """Build a disposable docs tree because autosummary writes source files.

    Keep root-level include targets beside the copied docs. Imports still use
    the measured checkout through the quality runner's explicit PYTHONPATH.
    Generated pages and notebook caches must never alter the user's sources.
    """
    root = work / "documentation"
    source = root / "docs"
    shutil.copytree(
        ROOT / "docs",
        source,
        ignore=shutil.ignore_patterns(
            "_build",
            "__pycache__",
            ".ipynb_checkpoints",
        ),
    )
    for name in ("README.md", "CHANGELOG.md", "LICENSE", "pyproject.toml"):
        shutil.copy2(ROOT / name, root / name)
    return [
        str(source) if arg == str(ROOT / "docs") else arg for arg in arguments
    ]


def enforce_coverage(output: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Treat missing reports as failures and enforce both coverage floors."""
    report = output / "coverage.json"
    if not report.exists():
        return {
            "exit_code": 1,
            "failures": ["Coverage JSON was not produced."],
        }
    totals = json.loads(report.read_text())["totals"]
    failures = coverage_failures(
        totals,
        config["statement-floor"],
        config["branch-floor"],
    )
    return {
        "exit_code": int(bool(failures)),
        "failures": failures,
        "totals": totals,
    }


def enforce_complexity(
    output: Path,
    command_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Validate exact Radon ranks; command success alone does not enforce A/B.
    """
    if command_result["exit_code"]:
        return command_result
    report = json.loads((output / "complexity.stdout.txt").read_text())
    failures = complexity_failures(report)
    return {
        **command_result,
        "exit_code": int(bool(failures)),
        "failures": failures,
    }


def execute_checks(names: list[str], output: Path) -> dict[str, Any]:
    """
    Run every requested gate even when an earlier gate reports violations.
    """
    config = settings()
    commands = check_commands(config, output)
    results = {}
    with tempfile.TemporaryDirectory(
        prefix=f"{config['package']}-quality-",
    ) as scratch:
        work = Path(scratch)
        env = test_environment(work, output)
        for name in names:
            arguments = commands[name]
            if name == "docs":
                arguments = isolated_documentation(work, arguments)
            # Lint file patterns resolve against cwd, even with --config.
            # Keep their caches in scratch while matching repository paths.
            check_work = ROOT if name in {"lint", "flake8", "format"} else work
            results[name] = run_process(
                name,
                arguments,
                check_work,
                env,
                output,
            )
        if "tests" in names:
            results["coverage-floor"] = enforce_coverage(output, config)
        if "complexity" in names:
            results["complexity"] = enforce_complexity(
                output,
                results["complexity"],
            )
    return results


def installed_versions() -> dict[str, str]:
    """
    Record installed distribution versions without environment credentials.
    """
    return {
        dist.metadata["Name"]: dist.version
        for dist in metadata.distributions()
    }


def main() -> int:
    """Collect fresh evidence and propagate any gate failure to the caller."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "check",
        choices=(*CHECKS, "all"),
        nargs="?",
        default="all",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = (args.output or ROOT / "quality/runs" / stamp).resolve()
    output.mkdir(parents=True, exist_ok=False)
    before = source_hashes()
    write_json(output / "source-hashes.json", before)
    names = list(CHECKS) if args.check == "all" else [args.check]
    if "lint" in names:
        names.append("flake8")
    results = execute_checks(names, output)
    if args.baseline:
        results["locked-environment"] = run_process(
            "locked-environment",
            [str(ROOT / "tools/quality_lock.py"), "verify"],
            ROOT,
            dict(os.environ),
            output,
        )
    unchanged = before == source_hashes()
    write_json(
        output / "manifest.json",
        {
            "commands": results,
            "source_unchanged": unchanged,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "packages": installed_versions(),
        },
    )
    print(f"Reports: {output}")
    return int(
        not unchanged or any(value["exit_code"] for value in results.values()),
    )


if __name__ == "__main__":
    raise SystemExit(main())
