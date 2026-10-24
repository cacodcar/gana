"""
Run pinned native gates and preserve commands, failures and core coverage.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from quality import run_process

ROOT = Path(__file__).resolve().parents[1]


def run(name, command, output, env):
    """Record the real command result without discarding failed checks."""
    try:
        return run_process(name, command, ROOT, env, output, executable=None)
    except OSError as error:
        (output / f"{name}.stdout.txt").write_text("")
        (output / f"{name}.stderr.txt").write_text(str(error) + "\n")
        return {"command": command, "exit_code": 127}


def core_coverage(cargo, output, env):
    """
    Measure Rust core regions/lines separately from Python branch coverage.
    """
    coverage_env = dict(env)
    coverage_env.update(
        RUSTFLAGS="-C instrument-coverage",
        LLVM_PROFILE_FILE=str(output / "raw/%m-%p.profraw"),
    )
    result = run(
        "coverage-test",
        [
            cargo,
            "test",
            "--locked",
            "--offline",
            "-p",
            "gana-core",
            "--lib",
            "--target-dir",
            str(ROOT / ".cache/coverage-target"),
            "--message-format=json",
        ],
        output,
        coverage_env,
    )
    binaries = []
    for line in (output / "coverage-test.stdout.txt").read_text().splitlines():
        if line.startswith("{"):
            artifact = json.loads(line)
            if artifact.get("executable"):
                binaries.append(artifact["executable"])
    llvm = Path(env["NATIVE_LLVM_BIN"])
    profiles = sorted((output / "raw").glob("*.profraw"))
    results = {"coverage-test": result}
    if not binaries or not profiles:
        results["coverage-data"] = {"exit_code": 1}
        return results
    data = str(output / "core.profdata")
    results["coverage-merge"] = run(
        "coverage-merge",
        [
            str(llvm / "llvm-profdata"),
            "merge",
            "-sparse",
            *map(str, profiles),
            "-o",
            data,
        ],
        output,
        env,
    )
    results["coverage-report"] = run(
        "coverage-report",
        [
            str(llvm / "llvm-cov"),
            "export",
            binaries[0],
            f"-instr-profile={data}",
            *map(str, sorted((ROOT / "crates/gana-core/src").glob("*.rs"))),
        ],
        output,
        env,
    )
    return results


def environment(output):
    """
    Keep dependency caches local and find compiler-matched LLVM utilities.
    """
    env = dict(os.environ)
    env.setdefault("CARGO_HOME", str(ROOT / ".cache/cargo"))
    rustc = shutil.which("rustc") or "rustc"
    run("rust-sysroot", [rustc, "--print", "sysroot"], output, env)
    run("rust-version", [rustc, "-vV"], output, env)
    sysroot = (output / "rust-sysroot.stdout.txt").read_text().strip()
    host = (output / "rust-version.stdout.txt").read_text()
    triple = next(
        (
            line.split(": ")[1]
            for line in host.splitlines()
            if line.startswith("host:")
        ),
        "unknown",
    )
    env.setdefault(
        "NATIVE_LLVM_BIN",
        str(Path(sysroot) / "lib/rustlib" / triple / "bin"),
    )
    return env


def main():
    """Fail if any native gate fails; retain raw evidence for every gate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = (
        args.output or ROOT / "quality/reports" / f"native-{stamp}"
    ).resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = environment(output)
    cargo = shutil.which("cargo") or "cargo"
    commands = {
        "format": [cargo, "fmt", "--all", "--check"],
        "tests": [cargo, "test", "--locked", "--offline", "-p", "gana-core"],
        "clippy": [
            cargo,
            "clippy",
            "--locked",
            "--offline",
            "--workspace",
            "--all-targets",
            "--",
            "-D",
            "warnings",
        ],
        "complexity": [
            str(ROOT / ".native-venv/bin/python"),
            "-m",
            "lizard",
            "-l",
            "rust",
            "-C",
            "10",
            "crates",
        ],
    }
    results = {
        name: run(name, command, output, env)
        for name, command in commands.items()
    }
    if (
        "release: 1.88.0\n"
        not in (output / "rust-version.stdout.txt").read_text()
    ):
        results["pinned-compiler"] = {"exit_code": 1}
    results.update(core_coverage(cargo, output, env))
    (output / "manifest.json").write_text(json.dumps(results, indent=2) + "\n")
    return int(any(result["exit_code"] for result in results.values()))


if __name__ == "__main__":
    raise SystemExit(main())
