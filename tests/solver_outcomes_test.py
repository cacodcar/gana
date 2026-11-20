"""Regression cases for deterministic solver failures and empty models."""

import builtins
from pathlib import Path

import pytest
from highspy import Highs, HighsModelStatus, HighsStatus, kHighsInf

from gana import Prg, V, inf
from gana.backends import highs


@pytest.mark.parametrize("bound", [0, -1])
def test_empty_model_checks_constant_row_and_offset(bound):
    model = Highs()
    model.changeObjectiveOffset(4)
    model.addRow(-kHighsInf, bound, 0, [], [])
    result = highs.optimize(model)
    assert model.getModelStatus() == HighsModelStatus.kModelEmpty
    assert result == (({}, 4, True) if bound == 0 else None)


def test_time_limit_without_feasible_incumbent():
    model = Highs()
    model.setOptionValue("presolve", "off")
    model.setOptionValue("time_limit", 0)
    model.addCol(1, 0, 100, 0, [], [])
    model.addRow(2, 100, 1, [0], [1.0])
    assert highs.optimize(model) is None
    assert model.getModelStatus() == HighsModelStatus.kTimeLimit


@pytest.mark.parametrize("missing", ["highspy", "unrelated_dependency"])
def test_solver_import_errors_identify_missing_dependency(
    monkeypatch, missing
):
    original = builtins.__import__

    def without_solver(name, globals_, locals_, fromlist, level):
        if name == "backends" and "highs" in fromlist:
            raise ModuleNotFoundError(missing, name=missing)
        return original(name, globals_, locals_, fromlist, level)

    program = Prg()
    with monkeypatch.context() as context:
        context.setattr(builtins, "__import__", without_solver)
        with pytest.raises(ModuleNotFoundError) as exc:
            program.opt(using="highs")
    if missing == "highspy":
        assert "gana[highs]" in str(exc.value)
    else:
        assert exc.value.name == missing
    assert program.n_formulations == program.n_solutions == 0


def test_failed_mps_import_does_not_register_formulation(monkeypatch):
    program = Prg()

    def invalid_mps(snapshot, stem):
        Path(stem + ".mps").write_text("not an MPS file\n", encoding="utf-8")

    monkeypatch.setattr(program, "_write_native_mps", invalid_mps)
    with pytest.raises(ValueError, match="could not read"):
        program.opt(using="highs")
    assert program.n_formulations == program.n_solutions == 0


def test_failed_optimizer_does_not_record_solution(monkeypatch):
    program = Prg()
    monkeypatch.setattr(Highs, "run", lambda _self: HighsStatus.kError)
    with pytest.raises(RuntimeError, match="failed to solve"):
        program.opt(using="highs")
    assert program.n_formulations == 1
    assert program.n_solutions == 0


def test_infeasible_gurobi_has_no_solution(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    program = Prg()
    program.x = V()
    program.cost = inf(program.x)
    program.upper = program.x <= -1
    program.opt()
    assert program.n_formulations == 1
    assert program.n_solutions == 0
