"""Verify the default solver and explicit Gurobi compatibility."""

import json

import gurobipy as gp
import pytest
from highspy import Highs, HighsModelStatus

from gana import Prg, T, V, inf


def demand_program(integer, compatibility):
    """Build an LP or MILP with a known optimum and objective offset."""
    program = Prg()
    program.units = V(itg=integer)
    program.demand = program.units >= 2.5
    program.cost = inf(4 * program.units + 1)
    if compatibility:
        program.demand[0].function.A[0] = -1
        assert program._native_export() is None
    return program


@pytest.mark.parametrize("compatibility", [False, True])
@pytest.mark.parametrize(
    ("integer", "units", "cost"), [(False, 2.5, 11), (True, 3, 13)]
)
def test_default_highs_solves_without_gurobi(
    monkeypatch, tmp_path, compatibility, integer, units, cost
):
    """An unqualified solve needs no Gurobi model or license."""
    monkeypatch.chdir(tmp_path)

    def unexpected_gurobi(*_args):
        pytest.fail("The default solver must not construct a Gurobi model")

    monkeypatch.setattr(Prg, "_build_gurobi", unexpected_gurobi)
    program = demand_program(integer, compatibility)
    program.opt()
    assert isinstance(program.formulation, Highs)
    assert program.formulation.getModelStatus() == HighsModelStatus.kOptimal
    assert program.solution.asdict() == {"units": [units]}
    assert program.obj() == pytest.approx(cost)
    assert program.n_solutions == 1
    assert (tmp_path / f"{program.name}.mps").is_file()
    program.export_solution(tmp_path / "result.json")
    record = json.loads((tmp_path / "result.json").read_text())
    assert record["status"] == "optimal"
    assert record["objective_value"] == pytest.approx(cost)


@pytest.mark.parametrize("compatibility", [False, True])
def test_explicit_gurobi_matches_default_solution(
    tmp_path, monkeypatch, compatibility
):
    """Explicit Gurobi retains solution-history and JSON parity."""
    monkeypatch.chdir(tmp_path)
    program = demand_program(True, compatibility)
    program.opt()
    program.export_solution(tmp_path / "highs.json")
    program.opt(using="gurobi")
    assert isinstance(program.formulation, gp.Model)
    assert program.formulation.Status == gp.GRB.OPTIMAL
    assert program.solution.asdict() == {"units": [3]}
    assert program.obj() == pytest.approx(13)
    assert program.n_solutions == 2
    program.export_solution(tmp_path / "gurobi.json")
    assert json.loads((tmp_path / "highs.json").read_text()) == json.loads(
        (tmp_path / "gurobi.json").read_text()
    )


def test_explicit_gurobi_infeasible_keeps_history_empty(tmp_path, monkeypatch):
    """An infeasible Gurobi solve still records no solution."""
    monkeypatch.chdir(tmp_path)
    program = demand_program(False, False)
    program.cap = program.units <= 2
    program.opt(using="gurobi")
    assert program.formulation.Status == gp.GRB.INFEASIBLE
    assert program.n_formulations == 1
    assert program.n_solutions == 0


def test_default_solver_rejects_unassigned_theta():
    """The default deterministic solve cannot discard parametric terms."""
    program = Prg()
    program.units, program.limit = V(), T(_=[(0, 1)])
    program.cap = program.units <= program.limit
    program.cost = inf(program.units)
    with pytest.raises(ValueError, match="Use solve"):
        program.opt()
    assert program.n_formulations == program.n_solutions == 0
