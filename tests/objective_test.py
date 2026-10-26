"""Independent scalar-objective, reduction and active-objective regressions."""

from operator import neg

import numpy as np
import pytest

from src.gana import I, P, Prg, T, V, inf, sigma, sup


def vector(size=3, **domain):
    """Make a registered vector with stable column IDs for numeric oracles."""
    program = Prg(name="objectives")
    program.i = I(size=size)
    program.x = V(program.i, **domain)
    return program


@pytest.mark.parametrize("compose", [inf, sup])
@pytest.mark.parametrize("kind", ["variable", "affine", "partial_sum"])
def test_reject_indexed_objective(compose, kind):
    """Multiple result rows require explicit reduction before composition."""
    p = vector()
    expressions = {"variable": p.x, "affine": 2 * p.x + 3}
    p.j = I(size=2)
    p.y = V(p.i, p.j)
    expressions["partial_sum"] = sigma(p.y, p.i)
    with pytest.raises(ValueError, match="scalar"):
        compose(expressions[kind])


@pytest.mark.parametrize("size", [1, 2, 3, 4])
@pytest.mark.parametrize("compose, sign", [(inf, 1), (sup, -1)])
def test_scalar_objective_coefficients(size, compose, sign):
    """Root reductions and their selected scalar rows compile identically."""
    p = vector(size)
    reduced = sigma(p.x)
    for expression in (reduced, reduced[0]):
        objective = compose(expression)
        np.testing.assert_array_equal(objective.C, [sign] * size)
        expected = dict.fromkeys(range(size), sign)
        np.testing.assert_equal(objective.matrix, expected)
    p.o = compose(reduced)
    np.testing.assert_array_equal(p.C, [sign] * size)


@pytest.mark.parametrize("size", [1, 2, 3, 4])
@pytest.mark.parametrize(
    "expression, coefficient, constant",
    [
        (lambda s: -s, -1, 0),
        (lambda s: neg(neg(s)), 1, 0),
        (lambda s: s + 3, 1, 3),
        (lambda s: 3 + s, 1, 3),
        (lambda s: s - 3, 1, -3),
        (lambda s: 3 - s, -1, 3),
        (lambda s: s + s, 2, 0),
        (lambda s: s - s, 0, 0),
        (lambda s: -2 * (s + 3), -2, -6),
        (lambda s: -(s + 3), -1, -3),
        (lambda s: s / -2, -0.5, 0),
    ],
)
def test_reduction_arithmetic(size, expression, coefficient, constant):
    """Assert exact coefficients and constants without symbolic equality."""
    p = vector(size)
    bound = 10
    p.c = expression(sigma(p.x)) <= bound
    np.testing.assert_array_equal(p.A, [[coefficient] * size])
    np.testing.assert_array_equal(p.B, [bound - constant])


@pytest.mark.parametrize("reflected", [False, True])
def test_partial_sum_negation(reflected):
    """Negating a partial reduction keeps its remaining coordinate rows."""
    p = vector()
    p.j = I(size=2)
    p.y = V(p.i, p.j)
    reduced = sigma(p.y, p.i)
    bound = 5
    p.c = bound <= reduced if reflected else reduced >= bound
    expected = np.zeros((2, 9))
    expected[0, 3::2] = -1
    expected[1, 4::2] = -1
    np.testing.assert_array_equal(p.A, expected)
    np.testing.assert_array_equal(p.B, [-5, -5])


@pytest.mark.parametrize("same_name", [False, True])
@pytest.mark.parametrize("domain", [{}, {"itg": True}, {"bnr": True}])
def test_active_objective_export(tmp_path, monkeypatch, same_name, domain):
    """Only the newest objective appears in matrices and solver columns."""
    gp = pytest.importorskip("gurobipy")
    monkeypatch.chdir(tmp_path)
    p = vector(2, **domain)
    p.cap = p.x <= 1
    p.o = inf(p.x[0])
    old = p.o
    name = "o" if same_name else "next_objective"
    setattr(p, name, sup(p.x[1]))
    active = getattr(p, name)
    np.testing.assert_array_equal(p.C, [0, -1])
    np.testing.assert_equal(p.objectives[0] is old, True)
    np.testing.assert_equal(p.objectives[-1] is active, True)
    p.mps()
    text = (tmp_path / "objectives.mps").read_text()
    np.testing.assert_equal(old.mps() in text.split(), False)
    with gp.read("objectives.mps") as model:
        np.testing.assert_array_equal(model.getAttr("Obj"), [0, -1])
        model.optimize()
        np.testing.assert_allclose(model.ObjVal, -1, rtol=0, atol=1e-9)


@pytest.mark.parametrize("compose, expected", [(inf, 3), (sup, -9)])
def test_objective_history(tmp_path, monkeypatch, compose, expected):
    """
    Export offsets and preserve solved history when replacing an objective.
    """
    gp = pytest.importorskip("gurobipy")
    monkeypatch.chdir(tmp_path)
    p = vector()
    bound = 2
    p.cap = p.x <= bound
    p.o = inf(sigma(p.x))
    p.opt()
    old = p.o
    np.testing.assert_allclose(old.X, 0, rtol=0, atol=1e-9)
    p.o = compose(sigma(p.x) + 3)
    p.opt()
    np.testing.assert_allclose(p.o.X, expected, rtol=0, atol=1e-9)
    np.testing.assert_allclose(old.X, 0, rtol=0, atol=1e-9)
    np.testing.assert_equal(p.n_solutions, 2)
    with gp.read("objectives.mps") as model:
        model.optimize()
        np.testing.assert_allclose(model.ObjVal, expected, rtol=0, atol=1e-9)


@pytest.mark.parametrize("size", [1, 2, 3, 4])
@pytest.mark.parametrize("reverse", [False, True])
def test_sum_with_vector_operand(size, reverse):
    """Broadcast a scalar reduction over each row of a distinct vector."""
    p = vector(size)
    p.y = V(p.i)
    reduced = sigma(p.x)
    expression = p.y - reduced if reverse else reduced - p.y
    bound = 7
    p.c = expression <= bound
    expected = np.hstack([np.ones((size, size)), -np.eye(size)])
    np.testing.assert_array_equal(p.A, -expected if reverse else expected)
    np.testing.assert_array_equal(p.B, [bound] * size)


@pytest.mark.parametrize("factor", [2, -2])
def test_reduction_parameter_scaling(factor):
    """A registered scalar parameter scales every term of a reduction."""
    p = vector()
    p.unit = I(size=1)
    p.rate = P(p.unit, _=factor)
    p.o = inf(p.rate * sigma(p.x))
    np.testing.assert_array_equal(p.C, [factor] * 3)


def test_parametric_objective_offset():
    """The ppopt adapter receives the active objective's signed constant."""
    p = vector(1)
    p.t = T(p.i, _=[(1, 2)])
    p.bound = p.x[0] <= p.t[0]
    p.o = inf(p.x[0] + 3)
    p.next_objective = sup(2 * p.x[0] + 5)
    formulation = p.ppopt()
    np.testing.assert_array_equal(formulation.c, [[-2]])
    np.testing.assert_array_equal(formulation.c_c, [[-5]])
