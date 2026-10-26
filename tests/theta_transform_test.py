"""Independent interval, ownership and display oracles for theta transforms."""

import operator
from unittest import TestCase

import numpy as np
import pytest

from gana import I, P, Prg, T, V

CHECK = TestCase()
LOWER_BOUND = 2


def model():
    """Provide positive, negative and zero-crossing intervals."""
    p = Prg()
    p.i = I(size=3)
    p.t = T(p.i, _=[(2, 5), (-5, -2), (-3, 5)])
    p.x = V(p.i)
    return p


@pytest.mark.parametrize("shape", ["root", "selection", "member"])
@pytest.mark.parametrize("factor", [-2, 0, 1, 2, np.float32(-2)])
@pytest.mark.parametrize("reverse", [False, True])
def test_scalar_bound_transform(shape, factor, reverse):
    """Every direct multiplication returns a new owner with ordered bounds."""
    p = model()
    source = {"root": p.t, "selection": p.t(p.i[::-2]), "member": p.t[1]}[
        shape
    ]
    before = source._validated_bounds()
    result = factor * source if reverse else source * factor
    expected = [
        sorted([float(factor) * lo, float(factor) * hi]) for lo, hi in before
    ]
    CHECK.assertIsInstance(result, T)
    CHECK.assertIsNot(result, source)
    CHECK.assertIs(result._owner_root, result)
    CHECK.assertEqual(tuple(result.map), tuple(source.map))
    np.testing.assert_array_equal(result._validated_bounds(), expected)
    CHECK.assertEqual(source._validated_bounds(), before)
    CHECK.assertEqual(p.n_thetas, 3)


@pytest.mark.parametrize("wrapper", [list, np.array, lambda v: P(_=v)])
@pytest.mark.parametrize("operation", [operator.mul, operator.truediv])
def test_vector_transform(wrapper, operation):
    """Coordinate order, not sign or value order, determines vector scaling."""
    p = model()
    source = p.t(p.i[::-1])
    factors = [-2, 4, -1]
    result = operation(source, wrapper(factors))
    expected = [
        sorted(operation(endpoint, factor) for endpoint in pair)
        for pair, factor in zip(source._validated_bounds(), factors)
    ]
    np.testing.assert_array_equal(result._validated_bounds(), expected)
    CHECK.assertEqual(tuple(result.map), tuple(source.map))


@pytest.mark.parametrize("wrapper", [list, np.array, lambda v: P(_=v)])
def test_reflected_vector_transform(wrapper):
    """Python, NumPy and P coefficients share T's transformation dispatch."""
    p = model()
    result = wrapper([-2, 4, -1]) * p.t
    CHECK.assertIsInstance(result, T)
    np.testing.assert_array_equal(
        result._validated_bounds(),
        [(-10, -4), (-20, -8), (-5, 3)],
    )


def test_negation_and_repeated_transforms():
    """Negation reverses endpoints; repeated transforms retain grouping."""
    p = model()
    negative = -p.t
    np.testing.assert_array_equal(
        negative._validated_bounds(),
        [(-5, -2), (2, 5), (-5, 3)],
    )
    CHECK.assertEqual(str(negative), "-t")
    repeated = -negative
    CHECK.assertEqual(str(repeated), "-(-t)")
    CHECK.assertEqual(repeated._validated_bounds(), p.t._validated_bounds())
    CHECK.assertIsNot(repeated, p.t)
    scaled = -2 * (3 * p.t)
    CHECK.assertEqual(str(scaled), "-2*(3*t)")
    np.testing.assert_array_equal(
        scaled._validated_bounds(),
        [(-30, -12), (12, 30), (-30, 18)],
    )


@pytest.mark.parametrize("factor", [-2, 0, 2])
def test_unbounded_intervals(factor):
    """Finite multiplication preserves infinite endpoints, with exact zero."""
    t = T(_=(-float("inf"), float("inf")))
    expected = [(0, 0)] if factor == 0 else [(-float("inf"), float("inf"))]
    CHECK.assertEqual((factor * t)._validated_bounds(), expected)


@pytest.mark.parametrize("factor", [float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("operation", [operator.mul, operator.truediv])
def test_nonfinite_factors_are_rejected(factor, operation):
    """Reject undefined endpoint products without touching model registries."""
    p = model()
    with pytest.raises(ValueError, match="finite coefficients"):
        operation(p.t, factor)
    CHECK.assertEqual(p.n_thetas, 3)


def test_registration_preserves_generated_name_and_reuses_owner():
    """Display labels survive automatic registration without becoming keys."""
    p = model()
    transformed = -2 * p.t
    CHECK.assertEqual(str(transformed), "-2*t")
    p.first = p.x <= transformed
    p.second = p.x >= transformed
    p.named = transformed
    CHECK.assertIs(p.named, transformed)
    CHECK.assertEqual(str(transformed), "-2*t")
    CHECK.assertEqual(p.n_theta_sets, 2)
    CHECK.assertEqual(p.n_thetas, 6)
    CHECK.assertTrue(
        all(member.parent is transformed for member in p.thetas[3:]),
    )
    np.testing.assert_array_equal(
        p.F,
        np.block(
            [[np.zeros((3, 3)), np.eye(3)], [np.zeros((3, 3)), -np.eye(3)]],
        ),
    )
    CHECK.assertEqual(p.t._validated_bounds(), [(2, 5), (-5, -2), (-3, 5)])


@pytest.mark.parametrize(
    "operation, separator",
    [(operator.add, " - "), (operator.sub, " + ")],
)
def test_signed_display_does_not_change_coefficients(operation, separator):
    """Readable subtraction is presentation only; T' keeps its own column."""
    p = model()
    negative = -2 * p.t
    expression = operation(p.x, negative)
    CHECK.assertEqual(str(expression), f"x{separator}2*t")
    CHECK.assertIn(separator, expression.longname)
    CHECK.assertIn(separator, expression.latex())
    p.row = expression <= 0
    sign = -1 if operation is operator.add else 1
    np.testing.assert_array_equal(
        p.F,
        np.hstack((np.zeros((3, 3)), sign * np.eye(3))),
    )
    CHECK.assertEqual(str(expression), f"x{separator}2*t")


def test_direct_subtraction_and_comparisons_keep_original_columns():
    """Compiler sign changes do not call the interval-negation operation."""
    p = model()
    p.cancel = p.t - p.t <= 0
    p.lower = p.t >= LOWER_BOUND
    p.reflected = 2 - p.t <= 0
    np.testing.assert_array_equal(
        p.F,
        np.vstack((np.zeros((3, 3)), np.eye(3), np.eye(3))),
    )
    np.testing.assert_array_equal(p.B, [0] * 3 + [-2] * 6)
    CHECK.assertEqual(p.n_thetas, 3)


def test_affine_scaling_retains_transformed_interval_reference():
    """Scaling a mixed expression scales coefficients, including T' terms."""
    p = model()
    transformed = -2 * p.t
    p.row = 3 * (p.x + transformed + 4) <= 0
    np.testing.assert_array_equal(p.A, 3 * np.eye(3))
    np.testing.assert_array_equal(
        p.F,
        np.hstack((np.zeros((3, 3)), -3 * np.eye(3))),
    )
    np.testing.assert_array_equal(p.B, [-12] * 3)
    CHECK.assertEqual(p.n_thetas, 6)
    CHECK.assertEqual(
        transformed._validated_bounds(),
        [(-10, -4), (4, 10), (-10, 6)],
    )


def test_negative_member_display_after_registration():
    """Scalar children retain readable signs in both plain text and LaTeX."""
    p = model()
    p.negative = -2 * p.t
    expression = p.x[1] + p.negative[1]
    CHECK.assertEqual(str(expression), "x[1] - 2*t[1]")
    CHECK.assertIn(" - ", expression.latex())
    p.row = expression <= 0
    np.testing.assert_array_equal(p.F, [[0, 0, 0, 0, -1, 0]])


def test_negated_theta_expression_keeps_original_owner():
    """Negating a composite theta expression only flips its coefficients."""
    p = model()
    p.row = -(p.t + p.t) <= 0
    np.testing.assert_array_equal(p.F, 2 * np.eye(3))
    CHECK.assertEqual(p.n_thetas, 3)
