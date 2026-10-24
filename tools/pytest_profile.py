"""
Automatic cProfile instrumentation for every repository pytest invocation.
"""

from __future__ import annotations

import cProfile
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from profile_context import (
    comparison_inputs,
    finish_inputs,
    package_roots,
    source_files,
    warm_property_framework,
)
from profile_stats import (
    Symbols,
    file_hashes,
    function_rows,
    save_report,
)


def pytest_addoption(parser: Any) -> None:
    """
    Offer explicit artifact/reference paths while profiling stays automatic.
    """
    group = parser.getgroup("function profiling")
    group.addoption(
        "--function-profile-output",
        metavar="DIR",
        help="Fresh directory for automatic cProfile artifacts",
    )
    group.addoption(
        "--function-profile-reference",
        metavar="REPORT",
        help="Compare with this prior profile.json or profile directory",
    )


def pytest_configure(config: Any) -> None:
    """Install a single profiling session, including direct pytest commands."""
    if not config.pluginmanager.hasplugin("research-function-profile"):
        config.pluginmanager.register(
            ProfileSession(config),
            "research-function-profile",
        )


def output_paths(config: Any, root: Path, run_id: str) -> tuple[Path, Path]:
    """Keep unique reports and a small compatible-run history index."""
    history = Path(
        os.environ.get(
            "PYTEST_FUNCTION_PROFILE_HISTORY",
            root / "quality/profiles",
        ),
    ).resolve()
    requested = config.getoption("function_profile_output") or os.environ.get(
        "PYTEST_FUNCTION_PROFILE_OUTPUT",
    )
    output = Path(requested).resolve() if requested else history / run_id
    worker = getattr(config, "workerinput", {}).get("workerid")
    if worker:
        output = output / worker
    output.mkdir(parents=True, exist_ok=False)
    return output, history


class ProfileSession:
    """
    Measure test phases and preserve useful reports even for failing tests.
    """

    def __init__(self, config: Any):
        """
        Initialize fresh output without enabling profiling during collection.
        """
        self.config = config
        self.root = Path(config.rootpath).resolve()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        self.run_id = f"{stamp}-{os.getpid()}"
        self.output, self.history = output_paths(
            config,
            self.root,
            self.run_id,
        )
        self.profile = cProfile.Profile()
        self.inputs: dict[str, Any] = {}
        self.before: dict[str, str] = {}
        self.outcomes: list[dict] = []
        self.tests: list[dict] = []
        self.comparison: dict[str, Any] = {}

    def pytest_collection_finish(self, session: Any) -> None:
        """Freeze workload identity before any fixture or test executes."""
        warm_property_framework(self.output)
        self.inputs = comparison_inputs(self.root, self.config, session.items)
        self.before = file_hashes(source_files(package_roots(self.root)))

    @pytest.hookimpl(wrapper=True, tryfirst=True)
    def pytest_runtest_protocol(self, item: Any):
        """Profile fixture setup, test execution and teardown together."""
        started = time.perf_counter()
        self.profile.enable()
        try:
            return (yield)
        finally:
            self.profile.disable()
            self.tests.append(
                {
                    "nodeid": item.nodeid,
                    "profiled_seconds": time.perf_counter() - started,
                },
            )

    def pytest_runtest_logreport(self, report: Any) -> None:
        """
        Keep phase outcomes separately from timing, including setup failures.
        """
        self.outcomes.append(
            {
                "nodeid": report.nodeid,
                "phase": report.when,
                "outcome": report.outcome,
            },
        )

    def build_report(self, exitstatus: int) -> dict[str, Any]:
        """Resolve measured code to stable IDs and report changing sources."""
        packages = package_roots(self.root)
        after = file_hashes(source_files(packages))
        unchanged = self.before == after
        inputs, identity = finish_inputs(self.inputs, self.outcomes)
        self.profile.create_stats()
        return {
            "run_id": self.run_id,
            "exit_code": int(exitstatus),
            "eligible": exitstatus == 0 and bool(self.tests) and unchanged,
            "scope": (
                "Fixture setup, test calls and teardown in this process's "
                "main thread; excludes collection/import startup and "
                "subprocess/thread internals."
            ),
            "comparison_inputs": inputs,
            "fingerprint": identity,
            "source_before": self.before,
            "source_after": after,
            "source_unchanged": unchanged,
            "package_origins": {
                name: str(path) for name, path in packages.items()
            },
            "tests": self.tests,
            "outcomes": self.outcomes,
            "functions": function_rows(
                self.profile.stats,
                Symbols(self.root, packages),
            ),
        }

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session: Any) -> None:
        """
        Save raw stats first, then rankings and a compatible-run comparison.
        """
        self.profile.disable()
        self.profile.dump_stats(str(self.output / "profile.pstats"))
        requested = self.config.getoption("function_profile_reference")
        reference = Path(requested).resolve() if requested else None
        report = self.build_report(int(session.exitstatus))
        self.comparison = save_report(
            self.output,
            self.history,
            report,
            reference,
        )

    def pytest_terminal_summary(self, terminalreporter: Any) -> None:
        """
        Point every invocation to its ranked functions and comparison status.
        """
        terminalreporter.write_sep(
            "-",
            "Function profile (instrumented diagnostics)",
        )
        terminalreporter.write_line(str(self.output / "profile.txt"))
        terminalreporter.write_line(
            "Comparison: " + self.comparison.get("status", "report pending"),
        )
