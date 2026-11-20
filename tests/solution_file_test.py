"""Exercise deterministic result files through Gana's public API."""

import json

import pytest

from gana import Prg, V, sup


def program(name, capacity=4):
    """Build the same named columns for distinct right-hand sides."""
    p = Prg(name=name)
    p.x, p.enabled = V(), V(bnr=True)
    p.cap = p.x <= capacity
    enabled = 1
    p.fix = p.enabled == enabled
    p.o = sup(3 * p.x + 2 * p.enabled + 5)
    return p


@pytest.mark.parametrize("legacy_solver_path", [False, True])
def test_round_trip_stored_solution(tmp_path, monkeypatch, legacy_solver_path):
    """Reattach a historical result across native and compatibility paths."""
    monkeypatch.chdir(tmp_path)
    original = program("original")
    rebuilt = program("rebuilt")
    exposed = original if legacy_solver_path else rebuilt
    # An explicit coefficient edit switches adapters without changing the row.
    exposed.cap[0].function.A[0] = 1
    assert exposed._native_export() is None

    original.opt()
    original.cap = original.x <= 9
    original.opt()
    path = tmp_path / "solution.json"
    original.export_solution(path, n_sol=0)
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record == {
        "format_version": 1,
        "values": {"V0": 4.0, "X1": 1.0},
        "objective_value": -19.0,
        "objective_sense": "min",
        "status": "optimal",
        "formulation_fingerprint": record["formulation_fingerprint"],
    }
    assert record["formulation_fingerprint"].startswith("sha256:")

    rebuilt.import_solution(path)
    assert rebuilt.solution.asdict() == {"x": [4.0], "enabled": [1.0]}
    assert rebuilt.obj() == -19.0
    assert rebuilt.x[0].X == {0: 4.0}
    assert not (tmp_path / "rebuilt.mps").exists()
    rebuilt.export_solution(tmp_path / "copy.json")
    assert (tmp_path / "copy.json").read_bytes() == path.read_bytes()

    original.export_solution(path)
    assert json.loads(path.read_text(encoding="utf-8"))["values"]["V0"] == 9.0


def test_changed_bound_rejected_without_loading(tmp_path, monkeypatch):
    """A matching column map is insufficient when the constraints differ."""
    monkeypatch.chdir(tmp_path)
    original = program("original")
    original.opt()
    original.export_solution("solution.json")

    changed = program("changed", capacity=5)
    before = [c._native_number_start for c in changed.constraint_sets]
    with pytest.raises(ValueError, match="fingerprint does not match"):
        changed.import_solution("solution.json")
    assert changed.solutions == changed.X == {}
    assert not changed.optimized
    assert changed.obj() is None
    assert [c._native_number_start for c in changed.constraint_sets] == before


@pytest.fixture
def saved_record(tmp_path, monkeypatch):
    """Generate a real record before testing malformed input and failed IO."""
    monkeypatch.chdir(tmp_path)
    p = program("original")
    p.opt()
    path = tmp_path / "solution.json"
    p.export_solution(path)
    return p, path


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("format_version", 2, "Unsupported solution format version"),
        ("format_version", True, "Unsupported solution format version"),
        ("formulation_fingerprint", "bad", "Invalid solution formulation"),
        ("objective_sense", "max", "minimization objective sense"),
        ("status", "infeasible", "solution status"),
        ("objective_value", False, "finite number"),
        ("values", {"V0": float("nan")}, "finite column values"),
        ("values", {"V0": 4}, "Invalid solution columns"),
    ],
)
def test_invalid_record_is_rejected(saved_record, field, value, error):
    """Validate malformed records before committing solution history."""
    _, path = saved_record
    record = json.loads(path.read_text(encoding="utf-8"))
    record[field] = value
    path.write_text(json.dumps(record), encoding="utf-8")
    receiver = program("receiver")
    with pytest.raises(ValueError, match=error):
        receiver.import_solution(path)
    assert receiver.solutions == receiver.X == {}


def test_unsolved_export_preserves_destination(tmp_path):
    """A missing solution fails before changing the destination."""
    path = tmp_path / "solution.json"
    path.write_text("original", encoding="utf-8")
    with pytest.raises(ValueError, match="No exportable deterministic"):
        program("unsolved").export_solution(path)
    assert path.read_text(encoding="utf-8") == "original"


def test_failed_replace_removes_temporary_file(saved_record, monkeypatch):
    """An interrupted replacement leaves the prior file intact."""
    p, path = saved_record
    before = path.read_bytes()
    files = set(path.parent.iterdir())

    def fail_replace(self, target):
        message = "injected replacement failure"
        raise OSError(message)

    monkeypatch.setattr(type(path), "replace", fail_replace)
    with pytest.raises(OSError, match="injected replacement failure"):
        p.export_solution(path)
    assert path.read_bytes() == before
    assert set(path.parent.iterdir()) == files
