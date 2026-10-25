"""Independent solver, MPS and solution-history checks for native adapters."""

from copy import deepcopy
from fractions import Fraction
from unittest import TestCase

import gurobipy as gp
import numpy as np
import pytest

from gana import I, P, Prg, V, inf, sigma

CHECK = TestCase()


def model(values=(-2, 0, 3), **domain):
    """
    Create a uniquely fixed affine model with an explicit objective offset.
    """
    p = Prg(name="native_adapter")
    p.i = I(size=len(values))
    p.x = V(p.i, mutable=True, **domain)
    p.k = P(p.i, _=list(range(1, len(values) + 1)))
    p.fixed = 2 * p.x == [2 * value for value in values]
    p.o = inf(sigma(p.k * p.x) + 7)
    return p


def untouched(p):
    """
    Native adapters must leave symbolic member states and scalar rows unborn.
    """
    for root in p.variable_sets:
        CHECK.assertEqual(root._symbol_storage.states, {})
    for constraint in p.constraint_sets:
        CHECK.assertNotIn("_legacy_cache", constraint.__dict__)


@pytest.mark.parametrize(
    "domain, values, kind",
    [
        ({"nn": False}, (-2, 0, 3), "C"),
        ({}, (1, 0, 3), "C"),
        ({"itg": True, "nn": False}, (-2, 0, 3), "I"),
        ({"itg": True}, (1, 0, 3), "I"),
        ({"bnr": True}, (0, 1, 1), "B"),
    ],
)
def test_solver_and_mps_domains(tmp_path, monkeypatch, domain, values, kind):
    """
    Both adapters agree with independent matrix, domain and optimum oracles.
    """
    monkeypatch.chdir(tmp_path)
    p = model(values, **domain)
    with p.gurobi() as direct, gp.read("native_adapter.mps") as parsed:
        for solver in (direct, parsed):
            np.testing.assert_array_equal(
                solver.getA().toarray(),
                2 * np.eye(3),
            )
            CHECK.assertEqual(solver.getAttr("VType"), [kind] * 3)
            CHECK.assertEqual(solver.ObjCon, 7)
            solver.Params.OutputFlag = 0
            solver.optimize()
            np.testing.assert_allclose(
                solver.getAttr("X"),
                values,
                rtol=0,
                atol=1e-9,
            )
    untouched(p)


def test_interleaved_domains_growth_and_solution(tmp_path, monkeypatch):
    """
    Integer-last export retains global IDs across interleaved owner growth.
    """
    monkeypatch.chdir(tmp_path)
    p = Prg(name="interleaved")
    p.i, p.j = I("a", "b"), I("c")
    p.x = V(p.i, itg=True, nn=False, mutable=True)
    p.r, p.b = V(p.i), V(p.i, bnr=True)
    p.x = V(p.j, itg=True, nn=False)
    p.fx, p.fr, p.fb = (
        2 * p.x == [-4, 8, 2],
        2 * p.r == [1, 3],
        2 * p.b == [0, 2],
    )
    p.o = inf(sigma(p.x) + sigma(p.r) + sigma(p.b) + 5)
    with p.gurobi() as solver:
        CHECK.assertEqual(
            solver.getAttr("VarName"),
            ["V2", "V3", "X4", "X5", "V0", "V1", "V6"],
        )
    p.opt()
    CHECK.assertEqual(
        p.solution.asdict(),
        {"x": [-2, 4, 1], "r": [0.5, 1.5], "b": [0, 1]},
    )
    CHECK.assertAlmostEqual(p.o.X, 11)
    untouched(p)


def test_redundant_and_cancelled_rows(tmp_path, monkeypatch):
    """
    Zero references and bound-only columns survive sparse export filtering.
    """
    monkeypatch.chdir(tmp_path)
    p = Prg(name="redundant")
    p.i = I(size=2)
    p.x = V(p.i)
    p.low = p.x >= 0
    limit = 5
    p.zero = p.x - p.x + 3 <= limit
    p.unused = V(p.i)
    p.mps("custom")
    with gp.read("custom.mps") as solver:
        CHECK.assertEqual(solver.getAttr("VarName"), ["V0", "V1"])
        CHECK.assertEqual(solver.getAttr("ConstrName"), ["C0", "C1"])
        np.testing.assert_array_equal(
            solver.getA().toarray(),
            np.zeros((2, 2)),
        )
        CHECK.assertEqual(solver.getAttr("RHS"), [2, 2])
    untouched(p)


def test_bulk_history_and_original_expression_values():
    """
    Deferred expression X uses solve-time values even after scalar history
    edits.
    """
    p = model(nn=False)
    p._load_values(([-2, 0, 3], 14))
    p._birth_solution()
    untouched(p)
    CHECK.assertEqual(p.solution.asdict(), {"x": [-2, 0, 3]})
    p.x[0].X[0] = 99
    CHECK.assertEqual(p.fixed.function[0].X[0], 0)
    CHECK.assertEqual(p.x[0].X[0], 99)
    CHECK.assertEqual(p.fixed.function.solution()[0], 202)


def test_held_history_observes_new_solutions():
    """
    Existing scalar history dictionaries update without rebuilding other
    members.
    """
    p = model(nn=False)
    history = p.x[0].X
    p._load_values(([-2, 0, 3], 14))
    CHECK.assertEqual(history, {0: -2})
    CHECK.assertEqual(list(p.x._symbol_storage.states), [0])
    p._birth_solution()
    p._load_values(([1, 2, 3], 21))
    CHECK.assertEqual(history, {0: -2, 1: 1})


@pytest.mark.parametrize("values", [[1], {}, {"V99": 2}])
def test_invalid_native_import_is_atomic(values):
    """
    Reject incomplete and unknown columns without creating any solution state.
    """
    p = model(nn=False)
    with pytest.raises(ValueError):
        p._load_values((values, 0))
    CHECK.assertEqual(p.X, {})
    untouched(p)


def test_solution_snapshot_and_growth():
    """
    Copies retain histories; newly appended members have no older solve value.
    """
    p = model(nn=False)
    p._load_values(([-2, 0, 3], 14))
    p._birth_solution()
    copied = deepcopy(p)
    CHECK.assertEqual(copied.solution.asdict(), p.solution.asdict())
    CHECK.assertEqual(copied.x[0].X, {0: -2})
    p.j = I("new")
    p.x = V(p.j, nn=False)
    CHECK.assertEqual(p.x[-1].X, {})
    CHECK.assertEqual(p.solution.asdict(), {"x": [-2, 0, 3]})


def test_scalar_domain_edit_is_respected(tmp_path, monkeypatch):
    """
    Explicit member-domain mutation stays authoritative without forced C
    replay.
    """
    monkeypatch.chdir(tmp_path)
    p = model([0, 1, 1])
    p.x[0].bnr = True
    with p.gurobi() as solver:
        CHECK.assertEqual(solver.getAttr("VarName"), ["X0", "V1", "V2"])
        CHECK.assertEqual(solver.getAttr("VType"), ["B", "C", "C"])


def test_exposed_constraint_uses_compatibility(tmp_path, monkeypatch):
    """
    An explicitly edited scalar row must override previously captured CSR data.
    """
    monkeypatch.chdir(tmp_path)
    p = model([1, 2, 3])
    row = p.fixed[0]
    row.function.A[0] = 4
    with p.gurobi() as solver:
        CHECK.assertEqual(solver.getA()[0, 0], 4)


def test_import_keeps_registration_row_numbers():
    """
    Loading values must not introduce the row-renumbering side effect of MPS.
    """
    p = model([1, 2, 3])
    limit = 10
    p.cap = 3 * p.x <= limit
    before = [c._native_number_start for c in p.constraint_sets]
    p._load_values(([1, 2, 3], 21))
    CHECK.assertEqual(
        [c._native_number_start for c in p.constraint_sets],
        before,
    )
    untouched(p)


def test_nonstandard_result_values_use_compatibility():
    """
    Preserve exact caller value types through the established scalar path.
    """
    p = model(nn=False)
    values = [Fraction(-2), Fraction(0), Fraction(3)]
    p._load_values((values, 14))
    CHECK.assertIsInstance(p.x[0].X[0], Fraction)
    CHECK.assertEqual(p.fixed.function.solution(), [0, 0, 0])


def test_failed_solver_construction_releases_model():
    """An adapter error must release an already-created solver resource."""
    p = model(nn=False)
    released = []

    class FailedModel:
        """Simulate an external solver rejecting variable construction."""

        def addMVar(self, *_args, **_kwargs):
            """Fail at the solver boundary before any constraints are added."""
            message = "solver rejected columns"
            raise ValueError(message)

        def dispose(self):
            """Record resource cleanup independently from numerical code."""
            released.append(True)

    with pytest.raises(ValueError, match="solver rejected columns"):
        p._native_export().gurobi("failed", lambda _name: FailedModel(), None)
    CHECK.assertEqual(released, [True])
    untouched(p)
