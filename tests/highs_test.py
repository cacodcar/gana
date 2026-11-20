"""Deterministic HiGHS solve and solution-history regressions."""

import json

import pytest
from highspy import HighsModelStatus

from gana import Prg, T, V, inf, sup


@pytest.mark.parametrize("compatibility", [False, True])
def test_highs_mip_record_and_gurobi_parity(
    tmp_path, monkeypatch, compatibility
):
    """Round-trip mixed domains and an offset through either export path."""
    monkeypatch.chdir(tmp_path)
    p = Prg()
    p.units = V(itg=True, nn=False)
    p.flag = V(bnr=True)
    p.spare = V()
    p.floor = p.units >= -2.7
    p.limit = p.flag <= 1
    p.cost = inf(3 * p.units - p.flag + 9)
    if compatibility:
        p.floor[0].function.A[0] = -1
        assert p._native_export() is None
    p.opt(using="highs")
    assert p.formulation.getModelStatus() == HighsModelStatus.kOptimal
    assert p.solution.asdict() == {
        "units": [-2.0],
        "flag": [1.0],
        "spare": [None],
    }
    assert p.obj() == pytest.approx(2)
    dest = tmp_path / "highs.json"
    p.export_solution(dest)
    record = json.loads(dest.read_text())
    assert record["status"] == "optimal"
    p.opt()
    p.export_solution(tmp_path / "gurobi.json")
    assert json.loads((tmp_path / "gurobi.json").read_text()) == record
    p.import_solution(dest)
    assert p.n_solutions == 3


def test_highs_infeasible_solve_keeps_previous_result():
    """An infeasible solve preserves the last successful result."""
    p = Prg()
    p.x = V()
    p.limit = p.x <= 2
    p.o = sup(p.x + 5)
    p.opt(using="highs")
    assert p.obj() == -7
    p.floor = p.x >= 3
    p.opt(using="highs")
    assert p.formulation.getModelStatus() == HighsModelStatus.kInfeasible
    assert p.n_solutions == 1
    assert p.solution.asdict() == {"x": [2.0]}


def test_highs_unbounded_has_no_solution():
    """A feasible point from an unbounded LP is not an incumbent optimum."""
    p = Prg()
    p.x = V()
    p.o = sup(p.x)
    p.opt(using="highs")
    assert p.formulation.getModelStatus() == HighsModelStatus.kUnbounded
    assert p.n_solutions == 0


def test_highs_rejects_unassigned_theta():
    """A deterministic solve cannot drop parametric constraint coefficients."""
    p = Prg()
    p.x, p.t = V(), T(_=[(0, 1)])
    p.limit = p.x <= p.t
    p.o = sup(p.x)
    with pytest.raises(ValueError, match="multiparametric"):
        p.opt(using="highs")
    assert p.n_formulations == 0
