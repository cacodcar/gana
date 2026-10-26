"""Independent value and matrix oracles for the audited operator defects."""

import operator
from unittest import TestCase

import numpy as np
import pytest

from gana import I, P, Prg, T, V
from gana.sets.constraint import C
from gana.sets.function import F

CHECK = TestCase()


@pytest.mark.parametrize("values", [0, -2.5, [2.5, -3.2, 8]])
@pytest.mark.parametrize("operand", [1, 2, [2, 4, 8], P(_=[2, 4, 8])])
@pytest.mark.parametrize(
    "operation",
    [operator.truediv, operator.floordiv, operator.mod, operator.pow],
)
def test_numeric_binary_values(values, operand, operation):
    """Numeric dunders agree with independently evaluated Python values."""
    parameter = P(_=values)
    left = values if isinstance(values, list) else [values] * 3
    right = operand._ if isinstance(operand, P) else operand
    right = right if isinstance(right, list) else [right] * 3
    expected = [operation(a, b) for a, b in zip(left, right)]
    result = operation(parameter, operand)
    if not isinstance(values, list) and isinstance(operand, int):
        expected = expected[:1]
    np.testing.assert_array_equal(
        result._ if isinstance(result, P) else [result],
        expected,
    )
    np.testing.assert_array_equal(
        parameter._,
        values if isinstance(values, list) else [values],
    )


@pytest.mark.parametrize(
    "operation",
    [operator.truediv, operator.floordiv, operator.mod],
)
@pytest.mark.parametrize("denominator", [0, P(_=0), [1, 0, 2], P(_=[1, 0, 2])])
def test_zero_numerator_still_checks_denominators(operation, denominator):
    """A zero numerator never hides a zero denominator in any coordinate."""
    with pytest.raises(ZeroDivisionError):
        operation(P(_=0), denominator)


@pytest.mark.parametrize(
    "operation",
    [operator.truediv, operator.floordiv, operator.mod, operator.pow],
)
@pytest.mark.parametrize("operand", [object(), [], [(1, 2)], T(_=(1, 2))])
def test_numeric_unsupported_operands(operation, operand):
    """Invalid numeric operands terminate with a type error, not recursion."""
    with pytest.raises(TypeError):
        operation(P(_=2), operand)


def test_parameter_unary_and_zero_power():
    """Unary plus and absolute value use the actual numeric values."""
    CHECK.assertEqual((+P(_=-2))._[0], -2)
    np.testing.assert_array_equal(abs(-P(_=[2, -4, 8]))._, [2, 4, 8])
    CHECK.assertEqual(P(_=0) ** 0, 1)
    with pytest.raises(ZeroDivisionError):
        P(_=0) ** -1


def test_numeric_coordinate_alignment():
    """Selections retain coordinates and mismatches cannot truncate."""
    p = Prg()
    p.i = I(size=3)
    p.data = P(p.i, _=[2, 4, 8])
    selected = p.data(p.i[::-1])
    quotient = selected / [2, 4, 8]
    np.testing.assert_array_equal(quotient._, [4, 1, 0.25])
    CHECK.assertEqual(tuple(quotient.map), tuple(selected.map))
    broadcast = P(_=8) / selected
    np.testing.assert_array_equal(broadcast._, [1, 2, 4])
    CHECK.assertEqual(tuple(broadcast.map), tuple(selected.map))
    with pytest.raises(ValueError):
        p.data / [1, 2]


@pytest.mark.parametrize(
    "kind",
    ["variable", "affine", "theta", "direct", "consistent"],
)
@pytest.mark.parametrize("operation", [operator.mul, operator.truediv])
def test_nonlinear_rejection(kind, operation):
    """Reject unsupported algebra before a constraint can pollute a program."""
    p = Prg()
    p.i = I(size=3)
    p.x, p.y = V(p.i), V(p.i)
    p.t = T(p.i, _=(1, 5))
    left = {"variable": p.x, "affine": 2 * p.x + 3, "theta": p.t}.get(
        kind,
        p.x,
    )
    with pytest.raises((ValueError, TypeError, NotImplementedError)):
        if kind in ("direct", "consistent"):
            F(
                one=left,
                two=p.y,
                mul=operation is operator.mul,
                div=operation is operator.truediv,
                consistent=kind == "consistent",
            )
        else:
            operation(left, p.y)
    CHECK.assertEqual(p.n_constraints, 0)
    CHECK.assertEqual(p.n_variables, 6)


@pytest.mark.parametrize("shape", ["vector", "member", "selection"])
def test_affine_list_division(shape):
    """List reciprocals scale coefficients and constants on actual rows."""
    p = Prg()
    p.i = I(size=3)
    p.x = V(p.i)
    columns = {"vector": [0, 1, 2], "member": [1], "selection": [2, 0]}[shape]
    x = {"vector": p.x, "member": p.x(p.i[1]), "selection": p.x(p.i[::-2])}[
        shape
    ]
    divisors = [2, -4, 8][: len(columns)]
    bound = 5
    p.row = (2 * x + 3) / divisors <= bound
    np.testing.assert_array_equal(
        p.A,
        2 * np.eye(3)[columns] / np.array(divisors)[:, None],
    )
    np.testing.assert_array_equal(p.B, 5 - 3 / np.array(divisors))


@pytest.mark.parametrize("registered", [False, True])
@pytest.mark.parametrize("operation", [operator.mul, operator.truediv])
@pytest.mark.parametrize("coefficient", [-2, [2, -2, 4], P(_=[2, -2, 4])])
def test_theta_bound_scaling(registered, operation, coefficient):
    """Registered and raw bounds agree, including negative scales."""
    p = Prg()
    p.i = I(size=3)
    bounds = [(1, 3), (2, 5), (3, 7)]
    theta = T(p.i, _=bounds)
    if registered:
        p.t = theta
    factors = coefficient._ if isinstance(coefficient, P) else coefficient
    factors = factors if isinstance(factors, list) else [factors] * 3
    expected = [
        sorted(operation(endpoint, factor) for endpoint in pair)
        for pair, factor in zip(bounds, factors)
    ]
    result = operation(theta, coefficient)
    np.testing.assert_array_equal(result._validated_bounds(), expected)
    np.testing.assert_array_equal(theta._validated_bounds(), bounds)
    CHECK.assertEqual(tuple(result.map), tuple(theta.map))


def test_theta_negation_and_invalid_scaling():
    """Negation orders endpoints; invalid denominators fail promptly."""
    p = Prg()
    p.t = T(_=(1, 3))
    np.testing.assert_array_equal((-p.t)._validated_bounds(), [(-3, -1)])
    np.testing.assert_array_equal(
        (0 * T(_=(-float("inf"), float("inf"))))._validated_bounds(),
        [(0, 0)],
    )
    with pytest.raises(ZeroDivisionError):
        p.t / 0
    with pytest.raises(TypeError):
        p.t * p.t
    with pytest.raises(ValueError):
        p.t * [1, 2]


@pytest.mark.parametrize("value", [2, [2, 4, 8]])
def test_theta_reflected_addition(value):
    """Reflection retains numeric constants and theta identity."""
    p = Prg()
    p.i = I(size=3)
    p.t = T(p.i, _=(1, 3))
    result = value + p.t
    CHECK.assertIsInstance(result, F)
    np.testing.assert_array_equal(
        result.B,
        [-2] * 3 if isinstance(value, int) else [-2, -4, -8],
    )
    CHECK.assertIs(result.two, p.t)


@pytest.mark.parametrize("subtract", [False, True])
def test_reflected_constraint_arithmetic(subtract):
    """Reflected constraint operators return a correctly signed affine row."""
    p = Prg()
    p.x = V()
    bound = 5
    constraint = p.x <= bound
    result = 2 - constraint if subtract else 2 + constraint
    CHECK.assertIsInstance(result, C)
    p.row = result
    np.testing.assert_array_equal(p.A, [[-1 if subtract else 1]])
    np.testing.assert_array_equal(p.B, [-7 if subtract else 3])
