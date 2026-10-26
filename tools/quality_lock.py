"""Create or verify a wheel-hashed, platform-specific quality environment.

Creation is explicit and never overwrites a prior lock. Install the recorded
closure with pip --require-hashes --only-binary=:all: --no-deps, then install
this checkout (and any recorded local dependencies) with --no-deps.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
import tomllib
from importlib import metadata
from pathlib import Path

from packaging.utils import canonicalize_name, parse_wheel_filename

ROOT = Path(__file__).resolve().parents[1]
# Keep the prior reference intact; this successor adds typing-only packages.
LOCK = ROOT / "requirements/quality-macos-x86_64-py313-typing20261023.lock"
MANIFEST = LOCK.with_suffix(".json")


def local_projects() -> set[str]:
    """
    Exclude editable source projects from wheel resolution, not from
    provenance.
    """
    with (ROOT / "pyproject.toml").open("rb") as stream:
        config = tomllib.load(stream)
    names = [
        config["project"]["name"],
        *config["tool"]["research-quality"].get("local-dependencies", []),
    ]
    return {canonicalize_name(name) for name in names}


def packages() -> dict[str, str]:
    """Read the complete installed non-local distribution closure."""
    excluded = local_projects()
    return {
        canonicalize_name(dist.metadata["Name"]): dist.version
        for dist in metadata.distributions()
        if canonicalize_name(dist.metadata["Name"]) not in excluded
    }


def source_fingerprints() -> dict[str, dict[str, str]]:
    """Record local project sources that cannot yet be fetched from PyPI."""
    result = {}
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    for name in config["tool"]["research-quality"].get(
        "local-dependencies",
        [],
    ):
        location = ROOT.parent / name
        result[name] = {
            str(path.relative_to(location)): hashlib.sha256(
                path.read_bytes(),
            ).hexdigest()
            for path in sorted((location / "src").rglob("*.py"))
        }
    return result


def identity() -> dict[str, str]:
    """Constrain rebuild claims to the measured interpreter and platform."""
    return {
        "python": platform.python_version(),
        "system": sys.platform,
        "machine": platform.machine(),
    }


def wheel_lines(folder: Path, expected: dict[str, str]) -> list[str]:
    """
    Hash every downloaded wheel and ensure the entire closure was captured.
    """
    wheels = {}
    for path in folder.glob("*.whl"):
        name, version, _, _ = parse_wheel_filename(path.name)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        wheels[canonicalize_name(name)] = (str(version), digest)
    if {name: item[0] for name, item in wheels.items()} != expected:
        message = "Downloaded wheels do not match the installed closure."
        raise ValueError(message)
    return [
        f"{name}=={version} --hash=sha256:{digest}"
        for name, (version, digest) in sorted(wheels.items())
    ]


def create() -> int:
    """Download exact wheels and preserve a new immutable reference lock."""
    if LOCK.exists() or MANIFEST.exists():
        message = (
            "A quality lock already exists; "
            "preserve it and review changes explicitly."
        )
        raise ValueError(message)
    expected = packages()
    with tempfile.TemporaryDirectory(prefix="quality-wheels-") as temporary:
        folder = Path(temporary)
        requirements = folder / "installed.txt"
        requirements.write_text(
            "\n".join(
                f"{name}=={version}"
                for name, version in sorted(expected.items())
            )
            + "\n",
        )
        # Reviewed: current Python runs pip on generated pinned requirements.
        subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--only-binary=:all:",
                "--no-deps",
                "-r",
                str(requirements),
                "--dest",
                str(folder),
            ],
            check=True,
            shell=False,
        )
        lines = wheel_lines(folder, expected)
    LOCK.parent.mkdir(exist_ok=True)
    LOCK.write_text(
        "#  platform-specific reference.\n" + "\n".join(lines) + "\n",
    )
    MANIFEST.write_text(
        json.dumps(
            {
                "identity": identity(),
                "packages": expected,
                "local_sources": source_fingerprints(),
                "lock_sha256": hashlib.sha256(LOCK.read_bytes()).hexdigest(),
            },
            indent=2,
        )
        + "\n",
    )
    return 0


def verify() -> int:
    """
    Fail on changed packages, platform, local dependencies or lock contents.
    """
    expected = json.loads(MANIFEST.read_text())
    checks = {
        "identity": expected["identity"] == identity(),
        "packages": expected["packages"] == packages(),
        "local_sources": expected["local_sources"] == source_fingerprints(),
        "lock_sha256": expected["lock_sha256"]
        == hashlib.sha256(LOCK.read_bytes()).hexdigest(),
    }
    print(json.dumps(checks, indent=2))
    return int(not all(checks.values()))


def main() -> int:
    """Expose explicit lock creation separately from routine verification."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    action = parser.parse_args().action
    return create() if action == "create" else verify()


if __name__ == "__main__":
    raise SystemExit(main())
