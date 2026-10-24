"""Numerical regressions for reciprocal coefficients and scalar reductions."""

from unittest import TestCase

import numpy as np
import pytest

from gana import I, P, Prg, V, inf, sigma
from gana.sets.function import F

CHECK = TestCase()


@pytest.mark.parametrize("values", [2, -4, [2], [2, -4, 8]])
@pytest.mark.parametrize("numerator", [1, -3, 0])
def test_numeric_reciprocal(values, numerator):
    """Evaluate actual quotients and retain detached, aligned coordinates."""
    parameter = P(_=values)
    original = tuple(parameter._)
    quotient = numerator / parameter
    expected = [numerator / value for value in original]
    CHECK.assertIsInstance(quotient, P)
    CHECK.assertIsNot(quotient, parameter)
    CHECK.assertEqual(tuple(quotient.map), tuple(parameter.map))
    np.testing.assert_array_equal(quotient._, expected)
    np.testing.assert_array_equal(list(quotient.map.values()), expected)
    np.testing.assert_array_equal(parameter._, original)


@pytest.mark.parametrize("values", [0, -0.0, [0], [2, 0, -4]])
@pytest.mark.parametrize("numerator", [1, 0])
def test_reciprocal_zero_denominator(values, numerator):
    """Zero denominators raise even for 0/0 without changing the input."""
    parameter = P(_=values)
    before = tuple(parameter._)
    with pytest.raises(ZeroDivisionError):
        numerator / parameter
    np.testing.assert_array_equal(parameter._, before)
    np.testing.assert_array_equal(list(parameter.map.values()), before)


def test_reciprocal_selected_coordinates():
    """Reordered multidimensional selections retain their numeric order."""
    p = Prg()
    p.i, p.j = I(size=2), I(size=2)
    p.data = P(p.i, p.j, _=[2, 4, -8, 16])
    selected = p.data(p.i[::-1], p.j)
    quotient = 1 / selected
    np.testing.assert_array_equal(quotient._, [-0.125, 0.0625, 0.5, 0.25])
    CHECK.assertEqual(tuple(quotient.map), tuple(selected.map))
    np.testing.assert_array_equal(p.data._, [2, 4, -8, 16])


@pytest.mark.parametrize("size", [1, 3])
@pytest.mark.parametrize("value", [2, -4])
def test_constant_reciprocal_broadcast(size, value):
    """Repeated numeric parameters stay valid coefficients after division."""
    p = Prg()
    p.i = I(size=size)
    p.x, p.data = V(p.i), P(p.i, _=value)
    bound = 3
    p.row = p.x / p.data <= bound
    np.testing.assert_array_equal(p.A, np.eye(size) / value)
    np.testing.assert_array_equal(p.B, [3] * size)


@pytest.mark.parametrize("kind", ["variable", "affine", "direct"])
def test_symbolic_division(kind):
    """Normal and inferred F division scale coefficients and constants."""
    p = Prg()
    p.i = I(size=3)
    p.x, p.data = V(p.i), P(p.i, _=[2, -4, 8])
    if kind == "direct":
        expression = F(one=p.x, two=p.data, div=True)
    elif kind == "affine":
        expression = (2 * p.x + 3) / p.data
    else:
        expression = p.x / p.data
    bound = 5
    p.row = expression <= bound
    coefficient = 2 if kind == "affine" else 1
    constant = 3 if kind == "affine" else 0
    reciprocal = np.array([0.5, -0.25, 0.125])
    np.testing.assert_array_equal(p.A, np.diag(coefficient * reciprocal))
    np.testing.assert_array_equal(p.B, 5 - constant * reciprocal)


@pytest.mark.parametrize("affine", [False, True])
def test_symbolic_zero_denominator(affine):
    """A failed division must not register partial constraints or columns."""
    p = Prg()
    p.i = I(size=2)
    p.x, p.data = V(p.i), P(p.i, _=[2, 0])
    expression = 2 * p.x + 3 if affine else p.x
    bound = 5
    with pytest.raises(ZeroDivisionError):
        p.row = expression / p.data <= bound
    CHECK.assertEqual(p.n_constraints, 0)
    CHECK.assertEqual(p.n_variables, len(p.i))


@pytest.mark.parametrize("shape", ["root", "selection", "indexless"])
@pytest.mark.parametrize(
    "build, coefficient, constant",
    [
        (lambda x: 2 * x, 2, 0),
        (lambda x: 2 * x + 3, 2, 3),
        (lambda x: -x, -1, 0),
        (lambda x: 3 - 2 * x, -2, 3),
        (lambda x: -(2 * x + 3), -2, -3),
        (lambda x: (2 * x + 3) / 2, 1, 1.5),
        (lambda x: x + x + 3, 2, 3),
    ],
)
def test_one_row_expression_sum(shape, build, coefficient, constant):
    """A scalar reduction preserves affine terms in objectives and rows."""
    p = Prg()
    p.i = I(size=3 if shape == "selection" else 1)
    p.x = V() if shape == "indexless" else V(p.i)
    column = 1 if shape == "selection" else 0
    variable = p.x(p.i[column]) if shape == "selection" else p.x
    expression = build(variable)
    reduced = sigma(expression)
    CHECK.assertIsInstance(reduced, F)
    p.o = inf(reduced)
    bound = 7
    p.row = reduced <= bound
    expected = np.zeros(p.n_variables)
    expected[column] = coefficient
    np.testing.assert_array_equal(p.C, expected)
    CHECK.assertEqual(p.o.constant, constant)
    np.testing.assert_array_equal(p.A, [expected])
    np.testing.assert_array_equal(p.B, [7 - constant])


def test_nested_scalar_reduction():
    """A repeated reduction preserves all columns of an existing sum."""
    p = Prg()
    p.i = I(size=3)
    p.x = V(p.i)
    bound = 7
    p.row = sigma(sigma(-2 * sigma(p.x) + 3)) <= bound
    np.testing.assert_array_equal(p.A, [[-2, -2, -2]])
    np.testing.assert_array_equal(p.B, [4])


def test_expression_member_sum_objective():
    """Reducing a selected expression row preserves its column and offset."""
    p = Prg()
    p.i = I(size=3)
    p.x = V(p.i)
    p.o = inf(sigma((2 * p.x + 3)[1]))
    np.testing.assert_array_equal(p.C, [0, 2, 0])
    CHECK.assertEqual(p.o.constant, 3)


def test_reciprocal_expression_snapshot():
    """Parameter replacement changes future divisions, not prior sums."""
    p = Prg()
    p.i = I(size=1)
    p.x, p.data = V(p.i), P(p.i, _=[2], mutable=True)
    quotient = 1 / p.data
    reduced = sigma((2 * p.x + 3) / p.data)
    with pytest.warns(UserWarning, match="overwritten"):
        p.data = P(p.i, _=[4])
    bound = 7
    p.old = reduced <= bound
    p.new = sigma((2 * p.x + 3) / p.data) <= bound
    np.testing.assert_array_equal(quotient._, [0.5])
    np.testing.assert_array_equal(p.A, [[1], [0.5]])
    np.testing.assert_array_equal(p.B, [5.5, 6.25])


def test_scalar_reduction_solve(tmp_path, monkeypatch):
    """The solver agrees with x=4 and (2*x+3)/2=5.5, including offset."""
    pytest.importorskip("gurobipy")
    monkeypatch.chdir(tmp_path)
    p = Prg(name="reciprocal_reduction")
    p.x, p.data = V(), P(_=2)
    lower_bound = 4
    p.lower = p.x >= lower_bound
    p.o = inf(sigma((2 * p.x + 3) / p.data))
    p.opt()
    np.testing.assert_allclose(p.o.X, 5.5, rtol=0, atol=1e-9)
