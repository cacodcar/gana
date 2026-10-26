"""Independent affine algebra and solver-export regressions.

Expected matrices are numerical oracles, not reconstructed from expression
metadata. Each case checks the public construction and compilation paths.
"""

import numpy as np
import pytest

from src.gana import I, P, Prg, T, V, inf, sigma


def vector(size=3):
    """Register two vectors in a deterministic column order."""
    program = Prg(name="affine")
    program.i = I(size=size)
    program.x = V(program.i)
    program.y = V(program.i)
    return program


@pytest.mark.parametrize(
    "expression, coefficients, rhs",
    [
        (lambda x, y: (x + 3) + (y + 4), (1, 1), 13),
        (lambda x, y: (x + 3) - (y + 4), (1, -1), 21),
        (lambda x, y: (2 * x + 3) + (3 * y - 4), (2, 3), 21),
        (lambda x, _y: (x - 3) + 1, (1, 0), 22),
        (lambda x, _y: (x + 3) - 1, (1, 0), 18),
        (lambda x, _y: (x - 3) - 1, (1, 0), 24),
        (lambda x, _y: 2 * x + (-3), (2, 0), 23),
        (lambda x, _y: -3 + 2 * x, (2, 0), 23),
        (lambda x, _y: 2 * (x + 3), (2, 0), 14),
        (lambda x, _y: -2 * (x - 3), (-2, 0), 14),
        (lambda x, _y: 5 - (x + 3), (-1, 0), 18),
        (lambda x, y: (x + y) - 3, (1, 1), 23),
    ],
)
@pytest.mark.parametrize("size", [1, 3, 4])
def test_affine_constants(expression, coefficients, rhs, size):
    """Preserve signs, constants and result rows through nested arithmetic."""
    p = vector(size)
    bound = 20
    p.c = expression(p.x, p.y) <= bound
    expected = np.hstack([c * np.eye(size) for c in coefficients])
    np.testing.assert_array_equal(p.A, expected)
    np.testing.assert_array_equal(p.B, np.full(size, rhs))
    np.testing.assert_equal(p.n_constraints, size)


@pytest.mark.parametrize("as_parameter", [False, True])
def test_vector_constants(as_parameter):
    """Lists and registered parameters obey the same elementwise algebra."""
    p = vector()
    left, right = [2, 3, 4], [1, 4, 2]
    if as_parameter:
        p.left = P(p.i, _=left)
        p.right = P(p.i, _=right)
        left, right = p.left, p.right
    bound = 7
    p.c = (p.x + left) - right <= bound
    np.testing.assert_array_equal(
        p.A,
        np.hstack([np.eye(3), np.zeros((3, 3))]),
    )
    np.testing.assert_array_equal(p.B, [6, 8, 5])


def test_repeated_terms_and_registration():
    """Accumulate duplicate columns and register each row/objective once."""
    p = vector()
    bound = 7
    p.c = p.x + p.x <= bound
    p.d = p.x - p.x == 0
    p.o = inf(p.x[0] + p.x[0] + 3 * p.x[1] - p.x[1])
    twice_identity = np.hstack([2 * np.eye(3), np.zeros((3, 3))])
    np.testing.assert_array_equal(p.G, twice_identity)
    np.testing.assert_array_equal(p.H, np.zeros((3, 6)))
    np.testing.assert_array_equal(
        p.A,
        np.vstack([twice_identity, np.zeros((3, 6))]),
    )
    np.testing.assert_array_equal(p.C, [2, 2, 0, 0, 0, 0])
    np.testing.assert_equal(p.c[0].matrix, {0: 2})
    np.testing.assert_equal(p.d[0].matrix, {0: 0})
    np.testing.assert_equal(len(p.x[0].cons_by), 2)
    np.testing.assert_equal(len(p.x[0].min_by), 1)


@pytest.mark.parametrize("size", [2, 3, 4])
def test_transport_rows(size):
    """Sums of selected scalars produce exactly one row per inequality."""
    p = Prg(name="transport")
    p.i = I(size=size)
    p.j = I(size=size)
    p.x = V(p.i, p.j)
    for n, i in enumerate(p.i):
        setattr(p, f"supply_{n}", sum(p.x(i, j) for j in p.j) <= 1)
    for n, j in enumerate(p.j):
        setattr(p, f"demand_{n}", sum(p.x(i, j) for i in p.i) >= 1)
    expected = np.zeros((2 * size, size * size))
    for n in range(size):
        start, stop = n * size, (n + 1) * size
        expected[n, start:stop] = 1
        expected[size + n, n::size] = -1
    np.testing.assert_array_equal(p.A, expected)
    np.testing.assert_array_equal(p.B, [1] * size + [-1] * size)


def test_multiscale_coefficients():
    """Repeat each coarse-scale coefficient over its fine-scale rows."""
    p = vector(4)
    p.k = I(size=2)
    p.rate = P(p.k, _=[2, 3])
    bound = 10
    p.c = p.rate * p.x + [1, 4] <= bound
    expected = np.hstack([np.diag([2, 2, 3, 3]), np.zeros((4, 4))])
    np.testing.assert_array_equal(p.A, expected)
    np.testing.assert_array_equal(p.B, [9, 9, 6, 6])


def test_mps_coefficients(tmp_path, monkeypatch):
    """Read exported coefficients independently with the solver's parser."""
    gp = pytest.importorskip("gurobipy")
    monkeypatch.chdir(tmp_path)
    p = vector(1)
    bound = 20
    p.c = (p.x + 3) + (p.x + 4) <= bound
    p.o = inf(p.x + p.x)
    p.mps()
    with gp.read("affine.mps") as model:
        np.testing.assert_array_equal(model.getA().toarray(), [[2]])
        np.testing.assert_array_equal(model.getAttr("RHS"), [13])
        np.testing.assert_array_equal(model.getAttr("Obj"), [2])


def test_reduction_plus_variable():
    """A sum used as an operand must produce ordinary compiled rows."""
    p = vector()
    bound = 10
    p.c = sigma(p.x) + p.y[0] <= bound
    np.testing.assert_array_equal(p.A, [[1, 1, 1, 1, 0, 0]])
    np.testing.assert_array_equal(p.B, [10])


@pytest.mark.parametrize(
    "kind",
    ["scalar", "list", "parameter", "constant_parameter"],
)
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("subtract", [False, True])
def test_negative_addends(kind, reverse, subtract):
    """Negative constants retain their signs in both operand orders."""
    p = vector()
    operand = {"scalar": -2, "list": [-2, -2, -2]}.get(kind)
    if kind in {"parameter", "constant_parameter"}:
        p.offset = P(
            p.i,
            _=-2 if kind == "constant_parameter" else [-2, -2, -2],
        )
        operand = p.offset
    expression = p.x + 3
    left, right = (operand, expression) if reverse else (expression, operand)
    bound = 10
    p.c = (left - right if subtract else left + right) <= bound
    sign = -1 if reverse and subtract else 1
    constant = -5 if reverse and subtract else (5 if subtract else 1)
    np.testing.assert_array_equal(
        p.A,
        np.hstack([sign * np.eye(3), np.zeros((3, 3))]),
    )
    np.testing.assert_array_equal(p.B, [10 - constant] * 3)


@pytest.mark.parametrize("factor", [-2, 2, [-2, 0, 3]])
def test_nested_scaling(factor):
    """Scale all columns and constants after combining compound expressions."""
    p = vector()
    expression = ((p.x + 3) + (2 * p.y - 4)) - 2
    bound = 10
    p.c = factor * expression <= bound
    factors = np.broadcast_to(factor, (3,))
    np.testing.assert_array_equal(
        p.A,
        np.hstack([np.diag(factors), 2 * np.diag(factors)]),
    )
    np.testing.assert_array_equal(p.B, 10 + 3 * factors)


def test_constants_before_parametric_rhs():
    """Preserve offsets when the program registers a vector of theta bounds."""
    p = vector()
    theta = T(p.i, _=[(0, 10)] * 3)
    p.c = (p.x + 2) - (p.y + 5) <= theta
    np.testing.assert_array_equal(p.A, np.hstack([np.eye(3), -np.eye(3)]))
    np.testing.assert_array_equal(p.B, [3, 3, 3])
    np.testing.assert_array_equal(p.F, np.eye(3))
    np.testing.assert_equal([(t.lb, t.ub) for t in p.thetas], [(0, 10)] * 3)
