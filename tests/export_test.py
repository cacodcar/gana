"""
Numerical oracles for variable domains, exported rows and named solutions.
"""

import itertools
import json
import pickle

import numpy as np
import pytest

from src.gana import I, Prg, T, V, inf, sup
from src.gana.sets.function import F


def vector(**domain):
    """Register one variable with a known exported column identifier."""
    program = Prg(name="export")
    program.i = I(size=1)
    program.x = V(program.i, **domain)
    return program


@pytest.mark.parametrize(
    "case",
    [
        ({"nn": False}, "C", -np.inf, -5.5, 3.75),
        ({}, "C", 0, 0, 3.75),
        ({"nn": False, "itg": True}, "I", -np.inf, -5, 3),
        ({"itg": True}, "I", 0, 0, 3),
        ({"bnr": True}, "B", 0, 0, 1),
    ],
)
def test_domains(tmp_path, monkeypatch, case):
    """
    Bounds and integrality survive MPS parsing, minimization and maximization.
    """
    gp = pytest.importorskip("gurobipy")
    domain, kind, lower, minimum, maximum = case
    monkeypatch.chdir(tmp_path)
    p = vector(**domain)
    lower_limit, upper_limit = -5.5, 3.75
    p.low = p.x >= lower_limit
    p.high = p.x <= upper_limit
    p.o = inf(p.x)
    p.mps()
    with gp.read("export.mps") as model:
        variable = model.getVarByName(p.x[0].mps())
        np.testing.assert_equal(variable.VType, kind)
        np.testing.assert_equal(variable.LB, lower)
        np.testing.assert_equal(variable.UB, 1 if kind == "B" else np.inf)
    p.opt()
    np.testing.assert_allclose(p.x[0].X[0], minimum, rtol=0, atol=1e-9)
    p.o = sup(p.x)
    p.opt()
    np.testing.assert_allclose(p.x[0].X[1], maximum, rtol=0, atol=1e-9)


@pytest.mark.parametrize("nonnegative", [False, True])
def test_explicit_nonnegativity(tmp_path, monkeypatch, nonnegative):
    """
    Omit a non-negativity row only when a declared bound already implies it.
    """
    gp = pytest.importorskip("gurobipy")
    monkeypatch.chdir(tmp_path)
    p = vector(nn=nonnegative)
    p.low = p.x >= 0
    p.o = inf(p.x)
    p.mps()
    text = (tmp_path / "export.mps").read_text()
    with gp.read("export.mps") as model:
        np.testing.assert_equal(model.NumConstrs, 0 if nonnegative else 1)
        if nonnegative:
            np.testing.assert_equal(p.low[0].mps() in text.split(), False)
        else:
            np.testing.assert_array_equal(model.getA().toarray(), [[-1]])
            np.testing.assert_equal(model.getVarByName("V0").LB, -np.inf)
        model.optimize()
        np.testing.assert_allclose(model.ObjVal, 0, rtol=0, atol=1e-9)


def reject_equality(_left, _right):
    """Make accidental symbolic comparisons in bookkeeping fail visibly."""
    message = "Bookkeeping invoked symbolic equality"
    raise AssertionError(message)


def test_domain_bookkeeping_uses_no_symbolic_equality(tmp_path, monkeypatch):
    """
    NN dimensions and export follow flags without constructing constraints.
    """
    monkeypatch.chdir(tmp_path)
    p = vector(nn=False)
    p.y = V(p.i)
    p.z = V(p.i, itg=True, nn=False)
    p.b = V(p.i, bnr=True)
    p.o = inf(p.x[0] + p.y[0] + p.z[0] + p.b[0])
    monkeypatch.setattr(V, "__eq__", reject_equality)
    np.testing.assert_array_equal(p.NN, [[0, -1, 0, 0], [0, 0, 0, -1]])
    np.testing.assert_equal(len(p.A_with_NN), len(p.B_with_NN))
    p.mps()


def test_mixed_domains_in_ppopt():
    """
    Free columns get no implicit non-negativity row or unmatched RHS entry.
    """
    p = vector(nn=False)
    p.y = V(p.i)
    p.t = T(p.i, _=[(1, 2)])
    p.balance = p.x[0] + p.y[0] == p.t[0]
    limit = 3
    p.cap = p.y <= limit
    p.o = inf(p.x[0])
    np.testing.assert_array_equal(p.NN, [[0, -1]])
    np.testing.assert_equal(len(p.A_with_NN), len(p.B_with_NN))
    model = p.ppopt()
    np.testing.assert_equal(model.A.shape[0], model.b.shape[0])
    np.testing.assert_equal(model.A.shape[0], model.F.shape[0])
    solution = model.solve_theta(np.array([[1.5]]))
    np.testing.assert_allclose(solution.sol, [-1.5, 3], rtol=0, atol=1e-9)


def mixed_program(order):
    """
    Give each domain a distinct fixed value, independent of declaration order.
    """
    p = Prg(name="mixed")
    p.i = I(size=1)
    domains = {
        "real": {},
        "integer": {"itg": True, "nn": False},
        "binary": {"bnr": True},
    }
    values = {"real": 2.25, "integer": -3, "binary": 1}
    for name in order:
        setattr(p, name, V(p.i, **domains[name]))
    for name, value in values.items():
        setattr(p, "fixed_" + name, getattr(p, name) == value)
    p.o = inf(p.real[0] + p.integer[0] + p.binary[0])
    return p, values


@pytest.mark.parametrize(
    "order",
    list(itertools.permutations(["real", "integer", "binary"])),
)
def test_solution_column_order(tmp_path, monkeypatch, order):
    """
    Map solver names to declarations when MPS groups integer columns last.
    """
    monkeypatch.chdir(tmp_path)
    p, values = mixed_program(order)
    p.opt()
    for name, expected in values.items():
        np.testing.assert_allclose(
            getattr(p, name)[0].X[0],
            expected,
            rtol=0,
            atol=1e-9,
        )
        np.testing.assert_allclose(
            p.solution.asdict()[name],
            [expected],
            rtol=0,
            atol=1e-9,
        )
    np.testing.assert_allclose(
        p.X[0],
        [values[name] for name in order],
        rtol=0,
        atol=1e-9,
    )


def test_objective_only_and_unused_columns(tmp_path, monkeypatch):
    """
    Load objective-only values by name and leave omitted unused columns
    unknown.
    """
    gp = pytest.importorskip("gurobipy")
    monkeypatch.chdir(tmp_path)
    p = vector(itg=True)
    p.unused = V(p.i, nn=False)
    p.cost = V(p.i)
    fixed = 4
    p.fixed = p.x == fixed
    p.o = inf(p.cost)
    p.opt()
    np.testing.assert_allclose(p.cost[0].X[0], 0, rtol=0, atol=1e-9)
    np.testing.assert_allclose(p.x[0].X[0], 4, rtol=0, atol=1e-9)
    with gp.read("export.mps") as model:
        np.testing.assert_equal(
            sorted(v.VarName for v in model.getVars()),
            ["V0", "V2"],
        )
    np.testing.assert_equal(p.unused[0].X[0], None)


@pytest.mark.parametrize("extension", ["json", "pkl"])
@pytest.mark.parametrize("named", [False, True])
def test_solution_import_order(tmp_path, monkeypatch, extension, named):
    """Read both legacy MPS-order lists and name-keyed JSON/pickle payloads."""
    monkeypatch.chdir(tmp_path)
    p, values = mixed_program(["integer", "real", "binary"])
    ordered = [2.25, 1, -3]
    payload = ({"X2": 1, "V0": -3, "V1": 2.25} if named else ordered, 0.25)
    path = tmp_path / f"solution.{extension}"
    if extension == "json":
        path.write_text(json.dumps(payload))
    else:
        path.write_bytes(pickle.dumps(payload))
    p.import_solution(str(path))
    for name, expected in values.items():
        np.testing.assert_allclose(
            getattr(p, name)[0].X[0],
            expected,
            rtol=0,
            atol=1e-9,
        )


def test_legacy_omitted_unused_variable():
    """An older positional file may omit unused columns, which stay unknown."""
    p = vector(itg=True)
    p.unused = V(p.i)
    p.y = V(p.i)
    fixed_x, fixed_y = 4, 2
    p.fixed_x = p.x == fixed_x
    p.fixed_y = p.y == fixed_y
    p.o = inf(p.y)
    p._load_values(([2, 4], 2))
    np.testing.assert_equal(p.x[0].X[0], 4)
    np.testing.assert_equal(p.y[0].X[0], 2)
    np.testing.assert_equal(p.unused[0].X[0], None)
    np.testing.assert_equal(p.X[0], [4, None, 2])


@pytest.mark.parametrize("values", [[1, 2], {}, {"V0": 1, "V99": 2}])
def test_invalid_import_does_not_change_history(values):
    """
    Reject missing/unknown names and wrong list lengths before storing values.
    """
    p = vector()
    p.fixed = p.x == 1
    p.o = inf(p.x)
    with pytest.raises(ValueError):
        p._load_values((values, 1))
    np.testing.assert_equal(p.X, {})
    np.testing.assert_equal(p.x[0].X, {})


def test_missing_unused_value_after_previous_solution():
    """
    A partial named import must not reuse an unused column's earlier value.
    """
    p = vector()
    p.unused = V(p.i)
    fixed = 2
    p.fixed = p.x == fixed
    p.o = inf(p.x)
    p._load_values(({"V0": 2, "V1": 7}, 2))
    p._birth_solution()
    p._load_values(({"V0": 2}, 2))
    p._birth_solution()
    np.testing.assert_equal(p.solution.asdict()["unused"], [None])
    np.testing.assert_equal(p.unused[0].X, {0: 7, 1: None})


def test_function_registration_uses_identity(monkeypatch):
    """
    Replacing the second expression must not overwrite an earlier expression.
    """
    p = vector()
    p.first = 2 * p.x
    p.second = 3 * p.x
    old_first = p.first
    replacement = 4 * p.x
    monkeypatch.setattr(F, "__eq__", reject_equality)
    p.second = replacement
    np.testing.assert_equal(p.function_sets[0] is old_first, True)
    np.testing.assert_equal(p.function_sets[1] is replacement, True)


def test_replacement_after_export(tmp_path, monkeypatch):
    """
    Replacing rows after solver renumbering updates the correct registrations.
    """
    gp = pytest.importorskip("gurobipy")
    monkeypatch.chdir(tmp_path)
    p = vector()
    p.y = V(p.i)
    original_balance = 2
    p.balance = p.x == original_balance
    limit = 5
    p.cap = p.y <= limit
    p.o = inf(p.x[0] + p.y[0])
    p.mps()
    new_balance = 3
    p.balance = p.y == new_balance
    p.mps()
    with gp.read("export.mps") as model:
        np.testing.assert_array_equal(model.getA().toarray(), [[0, 1], [0, 1]])
        np.testing.assert_array_equal(model.getAttr("RHS"), [5, 3])


def test_loaded_zero_in_constraint_evaluation(tmp_path, monkeypatch):
    """A loaded zero remains zero when evaluating an affine constraint."""
    monkeypatch.chdir(tmp_path)
    p = vector()
    p.fixed = 2 * p.x == 0
    p.o = inf(p.x)
    p.opt()
    np.testing.assert_array_equal(p.fixed.function.solution(), [0])


def test_feasibility_without_objective(tmp_path, monkeypatch):
    """A constant-zero objective supports solving a feasibility-only model."""
    monkeypatch.chdir(tmp_path)
    p = vector(nn=False)
    fixed = -2
    p.fixed = p.x == fixed
    p.opt()
    np.testing.assert_equal(p.solution.asdict()["x"], [fixed])


def test_only_redundant_row(tmp_path, monkeypatch):
    """A column remains present when its sole row is replaced by its bound."""
    gp = pytest.importorskip("gurobipy")
    monkeypatch.chdir(tmp_path)
    p = vector()
    p.low = p.x >= 0
    p.mps()
    with gp.read("export.mps") as model:
        np.testing.assert_equal(model.NumVars, 1)
        np.testing.assert_equal(model.NumConstrs, 0)
        np.testing.assert_equal(model.getVarByName("V0").LB, 0)


def test_constraint_replacement_changes_size(tmp_path, monkeypatch):
    """
    Shrinking and growing a row set preserves other rows and their columns.
    """
    gp = pytest.importorskip("gurobipy")
    monkeypatch.chdir(tmp_path)
    p = Prg(name="resize")
    p.i = I(size=3)
    p.x = V(p.i)
    limit = 5
    p.cap = p.x <= limit
    p.keep = p.x[2] == 1
    for size in (1, 3):
        selected = p.x[0] if size == 1 else p.x
        p.cap = selected <= limit
        p.mps()
        expected = np.vstack([np.eye(3)[:size], [0, 0, 1]])
        if size == 1:
            expected = expected[:, [0, 2]]
        with gp.read("resize.mps") as model:
            np.testing.assert_array_equal(model.getA().toarray(), expected)
        np.testing.assert_equal(p.n_constraints, size + 1)


def test_expression_replacement_preserves_objective():
    """
    Replacing a named function updates bookkeeping without retargeting
    objectives.
    """
    p = vector()
    p.first = 2 * p.x
    p.second = 3 * p.x
    p.o = inf(p.second)
    p.second = 4 * p.x
    np.testing.assert_array_equal(p.C, [3])
    np.testing.assert_equal(p.x[0].min_by[0] is p.o, True)
    np.testing.assert_equal(p.n_functions, len(p.functions))
    np.testing.assert_equal(
        [f.n for f in p.functions],
        list(range(p.n_functions)),
    )
