"""Verify native command failures remain reviewable quality failures."""

from unittest import TestCase

import native_quality
from native_quality import run
from profile_context import source_files

CHECK = TestCase()


def test_missing_native_tool_is_recorded(tmp_path):
    """An absent tool must not silently skip a gate or discard its error."""
    result = run("missing", [str(tmp_path / "does-not-exist")], tmp_path, {})
    CHECK.assertEqual(result["exit_code"], 127)
    CHECK.assertIn(
        "does-not-exist",
        (tmp_path / "missing.stderr.txt").read_text(),
    )


def test_launch_error_without_filename_keeps_executable(tmp_path, monkeypatch):
    """Windows launch errors may omit the filename; retain it explicitly."""
    message = "The system cannot find the file specified"

    def unavailable(*args, **kwargs):
        raise FileNotFoundError(message)

    monkeypatch.setattr(native_quality, "run_process", unavailable)
    command = [str(tmp_path / "missing-\u03b8")]
    result = run("missing", command, tmp_path, {})
    CHECK.assertEqual(result, {"command": command, "exit_code": 127})
    diagnostic = (tmp_path / "missing.stderr.txt").read_text(encoding="utf-8")
    CHECK.assertIn(command[0], diagnostic)
    CHECK.assertIn(message, diagnostic)


def test_profile_hash_inputs_include_native_binary(tmp_path):
    """Python-identical runs must still detect a changed extension binary."""
    (tmp_path / "_native.abi3.so").write_bytes(b"example")
    (tmp_path / "model.py").write_text("x = 1\n")
    (tmp_path / "ignored.txt").write_text("ignored")
    CHECK.assertEqual(
        set(source_files({"gana": tmp_path})),
        {"gana/_native.abi3.so", "gana/model.py"},
    )
