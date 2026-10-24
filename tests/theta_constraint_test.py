"""Independent parametric-row oracles for reflected operand normalization."""

from unittest import TestCase

import numpy as np
import pytest

from gana import I, P, Prg, T, V, inf
from gana.sets.function import F

CHECK = TestCase()


def model(size=3):
    """Register matching columns with distinct, unchanged theta intervals."""
    p = Prg()
    p.i = I(size=size)
    p.x = V(p.i, nn=False)
    p.t = T(p.i, _=[(n, n + 5) for n in range(size)])
    return p


@pytest.mark.parametrize(
    "relation, sign",
    [
        (lambda x, t: x >= t, -1),
        (lambda x, t: t <= x, -1),
        (lambda x, t: x <= t, 1),
        (lambda x, t: t >= x, 1),
    ],
)
@pytest.mark.parametrize("shape", ["vector", "member", "selection", "scalar"])
def test_theta_constraint_signs(relation, sign, shape):
    """Both comparison directions keep column IDs, signs and bound identity."""
    p = model()
    x, theta, columns = p.x, p.t, [0, 1, 2]
    if shape == "member":
        x, theta, columns = p.x[1], p.t[1], [1]
    elif shape == "selection":
        index = p.i[::-2]
        x, theta, columns = p.x(index), p.t(index), [2, 0]
    elif shape == "scalar":
        p = Prg()
        p.x, p.t = V(nn=False), T(_=(1, 5))
        x, theta, columns = p.x, p.t, [0]
    members = tuple(p.thetas)
    intervals = [(t.lb, t.ub) for t in members]
    p.row = relation(x, theta)
    expected = sign * np.eye(p.n_variables)[columns]
    np.testing.assert_array_equal(p.A, expected)
    np.testing.assert_array_equal(p.F, expected)
    np.testing.assert_array_equal(p.B, np.zeros(len(columns)))
    CHECK.assertEqual(len(p.thetas), len(members))
    CHECK.assertTrue(all(a is b for a, b in zip(p.thetas, members)))
    CHECK.assertEqual([(t.lb, t.ub) for t in p.thetas], intervals)


@pytest.mark.parametrize(
    "expression, coefficient, constant",
    [
        (lambda x: x, 1, 0),
        (lambda x: 2 * x + 3, 2, 3),
        (lambda x: -x, -1, 0),
    ],
)
def test_theta_left_subtraction(expression, coefficient, constant):
    """Normalize theta subtraction without relabeling the theta operand."""
    p = model()
    p.row = p.t - expression(p.x) <= 0
    np.testing.assert_array_equal(p.A, -coefficient * np.eye(3))
    np.testing.assert_array_equal(p.B, np.full(3, constant))
    np.testing.assert_array_equal(p.F, -np.eye(3))


@pytest.mark.parametrize("size", [1, 3])
def test_anonymous_theta_lower_bound(size):
    """Anonymous lower bounds receive one correct theta column per row."""
    p = Prg()
    p.i = I(size=size)
    p.x = V(p.i)
    p.row = p.x >= T(p.i, _=[(1, 4)] * size)
    np.testing.assert_array_equal(p.A, -np.eye(size))
    np.testing.assert_array_equal(p.F, -np.eye(size))
    CHECK.assertEqual(p.n_thetas, size)
    CHECK.assertEqual([(t.lb, t.ub) for t in p.thetas], [(1, 4)] * size)


@pytest.mark.parametrize(
    "variable_size, theta_size",
    [(4, 1), (4, 2), (2, 4), (1, 4)],
)
@pytest.mark.parametrize("lower", [False, True])
def test_broadcast_theta_rows(variable_size, theta_size, lower):
    """Repeat theta IDs by row alignment, including scalar RHS broadcasting."""
    p = Prg()
    p.i, p.j = I(size=variable_size), I(size=theta_size)
    p.x, p.t = V(p.i), T(p.j, _=[(0, 5)] * theta_size)
    p.row = p.x >= p.t if lower else p.x <= p.t
    sign = -1 if lower else 1
    variables = np.repeat(np.eye(variable_size), 4 // variable_size, axis=0)
    np.testing.assert_array_equal(p.A, sign * variables)
    expected = np.repeat(np.eye(theta_size), 4 // theta_size, axis=0)
    np.testing.assert_array_equal(p.F, sign * expected)


@pytest.mark.parametrize("operation", ["add", "sub", "mul"])
def test_inferred_normalization_types(operation):
    """Direct F construction uses resolved types through swap and negation."""
    p = model(2)
    p.k = P(p.i, _=[2, 4])
    left, right = (p.k, p.x) if operation in {"add", "sub"} else (p.x, p.k)
    p.row = F(one=left, two=right, **{operation: True}) <= 0
    coefficients = {"add": [1, 1], "sub": [-1, -1], "mul": [2, 4]}[operation]
    rhs = [-2, -4] if operation in {"add", "sub"} else [0, 0]
    np.testing.assert_array_equal(p.A, np.diag(coefficients))
    np.testing.assert_array_equal(p.B, rhs)


def test_foreign_theta_lower_bound_is_atomic():
    """A corrected lower bound still rejects a foreign symbolic owner."""
    p, q = model(), model()
    members = tuple(p.thetas)
    with pytest.raises(ValueError, match="another program"):
        p.row = p.x >= q.t
    CHECK.assertEqual(p.n_constraints, 0)
    CHECK.assertTrue(all(a is b for a, b in zip(p.thetas, members)))
    CHECK.assertTrue(all(not v.cons_by for v in p.x))


def test_theta_lower_bound_solver_adapter():
    """An independent LP solve agrees with the analytical optimum x = theta."""
    p = model(1)
    p.row = p.x >= p.t
    p.o = inf(2 * p.x[0] + 3)
    formulation = p.ppopt()
    solution = formulation.solve_theta(np.array([[1.5]]))
    np.testing.assert_allclose(solution.sol, [1.5], rtol=0, atol=1e-9)
    np.testing.assert_allclose(solution.obj, 6, rtol=0, atol=1e-9)
