"""Exercise mandatory native bootstrap through both existing import routes."""

import json
import os
import sys
from pathlib import Path

import pytest

pytest_plugins = ["pytester"]
ROOT = Path(__file__).resolve().parents[1]
PROBE = Path(__file__).with_name("backend_import_probe.py")


@pytest.fixture(params=["gana", "src.gana"])
def namespace(request):
    """Keep canonical and historical imports subject to the same contract."""
    return request.param


@pytest.fixture
def inspect_import(pytester, monkeypatch, namespace, plot_cache):
    """Run isolated imports with explicit source and temporary cache paths."""
    monkeypatch.setenv(
        "PYTHONPATH", os.pathsep.join((str(ROOT), str(ROOT / "src")))
    )
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setenv("MPLCONFIGDIR", str(plot_cache))

    def inspect(setting=None, failure="none"):
        """Control only this child process's selected backend and loader."""
        if setting is None:
            monkeypatch.delenv("GANA_BACKEND", raising=False)
        else:
            monkeypatch.setenv("GANA_BACKEND", setting)
        result = pytester.run(
            sys.executable, "-B", str(PROBE), namespace, failure, timeout=60
        )
        assert result.ret == 0, result.stderr.str()
        return json.loads(result.stdout.lines[-1])

    return inspect


@pytest.fixture(scope="module")
def plot_cache(tmp_path_factory):
    """Share only disposable font metadata across isolated import processes."""
    return tmp_path_factory.mktemp("backend-import-matplotlib")


@pytest.mark.parametrize("setting", [None, "rust-parameters"])
def test_supported_settings_register_native_model(inspect_import, setting):
    """Default and old native settings preserve known model matrices."""
    assert inspect_import(setting) == {
        "backend": "rust-parameters",
        "native": True,
        "native_parameter": True,
        "values": [2, 3],
        "A": [[1, 0], [0, 1]],
        "B": [2, 3],
        "C": [2, 3],
    }


def test_retired_python_setting_is_actionable(inspect_import):
    """A retired setting cannot quietly select a different implementation."""
    result = inspect_import("python")
    assert result["error"] == "ValueError"
    assert "no longer supported" in result["message"]
    assert "unset GANA_BACKEND" in result["message"]


@pytest.mark.parametrize("setting", ["unknown", ""])
def test_invalid_setting_is_rejected(inspect_import, setting):
    """Reject unknown and explicitly empty configuration settings."""
    result = inspect_import(setting)
    assert result["error"] == "ValueError"
    assert "Unknown GANA_BACKEND" in result["message"]


@pytest.mark.parametrize("setting", [None, "rust-parameters"])
def test_missing_extension_explains_installation(inspect_import, setting):
    """Require the extension and retain the original missing-module cause."""
    result = inspect_import(setting, "missing")
    assert result["error"] == "ModuleNotFoundError"
    assert result["name"] == "gana._native"
    assert "requires its Rust extension" in result["message"]
    assert "wheel" in result["message"]
    assert "python -m pip install ." in result["message"]
    assert result["cause"] == "ModuleNotFoundError"
    assert result["cause_name"] == "gana._native"
    assert result["cause_message"] == "No module named 'gana._native'"


@pytest.mark.parametrize("setting", [None, "rust-parameters"])
@pytest.mark.parametrize(
    ("failure", "error", "name", "message"),
    [
        (
            "dependency",
            "ModuleNotFoundError",
            "native_dependency",
            "No module named 'native_dependency'",
        ),
        (
            "abi",
            "ImportError",
            "gana._native",
            "Native loader rejected an incompatible binary",
        ),
    ],
)
def test_other_loader_errors_are_preserved(
    inspect_import, setting, failure, error, name, message
):
    """Keep dependency and binary-load errors distinct from missing wheels."""
    result = inspect_import(setting, failure)
    assert result == {
        "error": error,
        "message": message,
        "name": name,
        "cause": None,
        "cause_name": None,
        "cause_message": None,
    }
