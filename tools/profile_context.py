"""
Capture explicit, non-secret comparison inputs for test function profiles.
"""

from __future__ import annotations

import cProfile
import os
import platform
import sys
import time
from importlib import metadata
from pathlib import Path
from typing import Any

from profile_stats import SCHEMA, file_hashes, fingerprint, write_json

PROJECTS = ("gana", "energia", "vael")
THREAD_VARIABLES = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "NUMBA_NUM_THREADS",
    "PYTHONHASHSEED",
    "LC_ALL",
    "LANG",
    "TZ",
)


def package_roots(root: Path) -> dict[str, Path]:
    """Include the tested package and loaded local research dependencies."""
    result = {
        p.name: p.resolve()
        for p in (root / "src").glob("*")
        if (p / "__init__.py").is_file()
    }
    for name in PROJECTS:
        module = sys.modules.get(name) or sys.modules.get("src." + name)
        filename = getattr(module, "__file__", None)
        if filename:
            result[name] = Path(filename).resolve().parent
    return result


def source_files(packages: dict[str, Path]) -> dict[str, Path]:
    """Identify exact package source bytes, including editable dependencies."""
    return {
        f"{name}/{path.relative_to(root)}": path
        for name, root in packages.items()
        for path in root.rglob("*")
        if path.suffix in {".py", ".pyi", ".so", ".pyd"}
        and "__pycache__" not in path.parts
    }


def workload_files(root: Path, items: list) -> dict[str, Path]:
    """
    Hash collected tests, helpers and local test data independently of src.
    """
    paths = set((root / "tests").rglob("*"))
    paths.update(Path(item.path) for item in items)
    paths.add(root / "conftest.py")
    return {
        str(path.relative_to(root)): path
        for path in paths
        if path.is_file()
        and path.is_relative_to(root)
        and "__pycache__" not in path.parts
    }


def instrumentation(root: Path, config: Any) -> dict[str, Any]:
    """Separate profiled coverage runs from profiles without coverage."""
    files = {
        name: root / "tools" / name
        for name in (
            "profile_context.py",
            "profile_stats.py",
            "pytest_profile.py",
        )
    }
    return {
        "schema": SCHEMA,
        "implementation": file_hashes(files),
        "coverage": bool(config.getoption("cov_source", default=None)),
        "coverage_branch": bool(config.getoption("cov_branch", default=False)),
        "hypothesis_seed": config.getoption("hypothesis_seed", default=None),
        "scope": "pytest setup/call/teardown, main thread",
    }


def environment() -> dict[str, Any]:
    """
    Record host/runtime/dependencies without dumping credentials or paths.
    """
    versions = {
        dist.metadata["Name"]: dist.version
        for dist in metadata.distributions()
    }
    dependencies = {
        k: v
        for k, v in versions.items()
        if k.lower() not in {"gana", "energiapy", "vael"}
    }
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "host": platform.node(),
        "processor": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "dependencies": dependencies,
        "settings": {name: os.environ.get(name) for name in THREAD_VARIABLES},
    }


def implementation_identity() -> dict[str, str | None]:
    """Record loaded implementations without importing optional dependencies.

    None means the extension identity is unavailable in this process. Binary
    bytes remain in source hashes so compatible code changes can be measured.
    """
    native = sys.modules.get("gana._native")
    return {"gana": getattr(native, "BACKEND", None)}


def comparison_inputs(root: Path, config: Any, items: list) -> dict[str, Any]:
    """Define matching workload, hardware and instrumentation requirements."""
    return {
        "environment": environment(),
        "implementations": implementation_identity(),
        "instrumentation": instrumentation(root, config),
        "nodeids": [item.nodeid for item in items],
        "workload_hashes": file_hashes(workload_files(root, items)),
    }


def finish_inputs(
    inputs: dict[str, Any],
    outcomes: list[dict],
) -> tuple[dict, str]:
    """
    Include actual outcomes so skipped and executed workloads never match.
    """
    complete = {**inputs, "outcomes": outcomes}
    return complete, fingerprint(complete)


def warm_property_framework(output: Path) -> None:
    """Profile Hypothesis's lazy module scan before its per-input time budget.

    The pinned Hypothesis 6.142.3 provider initializes its constant pool
    lazily.
    Scanning thousands of loaded modules can exceed its one-second generation
    health check before any meaningful input generation. Initialize only that
    cache after collection; never change strategies, settings or health checks.
    The internal optional hook is detected explicitly for other environments.
    """
    provider = sys.modules.get("hypothesis.internal.conjecture.providers")
    initialize = getattr(provider, "_get_local_constants", None)
    report: dict[str, Any] = {
        "status": "unavailable",
        "scope": "Hypothesis constant-pool initialization",
    }
    if callable(initialize):
        profile = cProfile.Profile()
        started = time.perf_counter()
        profile.runcall(initialize)
        report = {
            **report,
            "status": "initialized",
            "profiled_seconds": time.perf_counter() - started,
        }
        profile.dump_stats(str(output / "hypothesis-startup.prof"))
    write_json(output / "hypothesis-startup.json", report)
