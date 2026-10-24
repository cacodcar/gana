"""Independent numerical and ownership checks for native affine batches."""

from copy import deepcopy
from importlib import import_module
from unittest import TestCase

import numpy as np
import pytest

from gana import I, P, Prg, T, V, inf, sigma, sup
from gana.backends.native.algebra import NativeRows
from gana.storage.parameters import NATIVE

CHECK = TestCase()
pytestmark = pytest.mark.skipif(not NATIVE, reason="requires native algebra")


def model(size=6):
    """
    Register coefficients and variables without requesting scalar members.
    """
    p = Prg()
    p.i = I(size=size)
    p.x = V(p.i, mutable=True)
    p.k = P(p.i, _=list(range(1, size + 1)), mutable=True)
    return p


def test_weighted_objective_never_materializes_members():
    """
    Construction, reduction, registration and coefficient export stay bulk.
    """
    p = model(1000)
    expression = p.k * p.x
    CHECK.assertIsInstance(expression, NativeRows)
    reduced = sigma(expression)
    CHECK.assertIsInstance(reduced, NativeRows)
    p.o = inf(reduced)
    np.testing.assert_array_equal(p.C, np.arange(1, 1001))
    CHECK.assertEqual(p.x._symbol_storage.states, {})
    CHECK.assertNotIn("_legacy_cache", expression.__dict__)
    CHECK.assertNotIn("_legacy_cache", reduced.__dict__)


def test_named_expression_registration_is_lazy_and_keeps_row_identity():
    """Program bookkeeping counts native rows before callers request them."""
    p = model(3)
    p.expense = p.k * p.x
    p.total = sigma(p.expense)
    p.o = inf(p.total)
    CHECK.assertEqual(p.n_functions, 4)
    np.testing.assert_array_equal(p.C, [1, 2, 3])
    CHECK.assertEqual(p.x._symbol_storage.states, {})
    CHECK.assertIs(p.expense[1].parent, p.expense)
    CHECK.assertEqual([row.n for row in p.functions], list(range(4)))


@pytest.mark.parametrize("compose,sign", [(inf, 1), (sup, -1)])
def test_repeated_terms_and_integer_constants(compose, sign):
    """Repeated columns accumulate while scalar offsets survive reduction."""
    p = model()
    expression = 2 * (p.k * p.x + p.x) - p.x + 3
    p.o = compose(sigma(expression))
    np.testing.assert_array_equal(p.C, sign * (2 * np.arange(1, 7) + 1))
    CHECK.assertEqual(p.o.constant, sign * 18)
    CHECK.assertEqual(p.x._symbol_storage.states, {})


def test_broadcast_and_reversed_selections_keep_order():
    """Two coefficients repeat consecutively over six reversed variable IDs."""
    p = model()
    p.j = I(size=2)
    p.c = P(p.j, _=[2, -3])
    p.o = inf(sigma(p.c * p.x(p.i[::-1])))
    np.testing.assert_array_equal(p.C, [-3, -3, -3, 2, 2, 2])
    CHECK.assertEqual(p.x._symbol_storage.states, {})


@pytest.mark.parametrize("axis", [0, 1])
def test_axis_reductions_match_independent_dense_rows(axis):
    """Native reductions preserve row coordinates and original column order."""
    p = Prg()
    p.i, p.j = I(size=2), I(size=3)
    p.x = V(p.i, p.j)
    p.k = P(p.i, p.j, _=[1, 2, 3, 4, 5, 6])
    reduced = sigma(p.k * p.x, (p.i, p.j)[axis], position=axis)
    CHECK.assertIsInstance(reduced, NativeRows)
    CHECK.assertEqual(p.x._symbol_storage.states, {})
    bound = 10
    p.c = reduced <= bound
    expected = np.zeros((3 if axis == 0 else 2, 6))
    for column in range(6):
        row = column % 3 if axis == 0 else column // 3
        expected[row, column] = column + 1
    np.testing.assert_array_equal(p.A, expected)
    np.testing.assert_array_equal(p.B, [10] * len(expected))


def test_numeric_capture_and_owner_growth_do_not_rewrite_expressions():
    """Later edits cannot change captured coefficients or add new columns."""
    p = model(3)
    expression = p.k * p.x
    p.k._[:] = [9, 9, 9]
    p.j = I("extra")
    p.x = V(p.j)
    p.o = inf(sigma(expression))
    np.testing.assert_array_equal(p.C, [1, 2, 3, 0])
    CHECK.assertEqual(p.x._symbol_storage.states, {})
    np.testing.assert_array_equal(
        [row.A for row in expression],
        [[1], [2], [3]],
    )


def test_objective_links_cover_live_and_later_materialized_members():
    """Replacement detaches old links, including repeated variable terms."""
    p = model(3)
    held = p.x[0]
    p.o = inf(sigma(p.x + p.x))
    old = p.o
    CHECK.assertEqual(held.min_by, [old])
    CHECK.assertEqual(p.x[1].min_by, [old])
    p.o = inf(sigma(p.x(p.i[1:])))
    CHECK.assertEqual(held.min_by, [])
    CHECK.assertEqual(p.x[1].min_by, [p.o])
    CHECK.assertEqual(p.x[2].min_by, [p.o])


@pytest.mark.parametrize("materialize", [False, True])
def test_native_objective_deepcopy_restores_shared_member_identity(
    materialize,
):
    """
    Whole-program serialization preserves coefficients and objective links.
    """
    p = model(3)
    p.o = inf(sigma(p.k * p.x))
    if materialize:
        list(p.o.variables)
    restored = deepcopy(p)
    np.testing.assert_array_equal(restored.C, [1, 2, 3])
    CHECK.assertIs(restored.o.variables[0], restored.x[0])
    CHECK.assertEqual(restored.x[0].min_by, [restored.o])


@pytest.mark.parametrize("power", [60, 120, 140])
def test_large_coefficients_preserve_existing_parameter_conversion(power):
    """
    P already converts numeric inputs to float before compiling expressions.
    """
    p = model(2)
    coefficient = 2**power + 1
    p.o = inf(sigma(coefficient * p.x + p.x))
    CHECK.assertEqual(p.C, [float(coefficient) + 1] * 2)
    CHECK.assertIsInstance(p.C[0], float)


def test_large_float_products_preserve_existing_range():
    """
    A large exactly representable floating product must not narrow to i128.
    """
    p = model(2)
    p.o = inf(sigma((2**120 * p.x) * 1024))
    CHECK.assertEqual(p.C, [2**130] * 2)


def test_float_constant_reduction_retains_compensated_python_sum():
    """Cancellation-sensitive constants preserve Python's reduction result."""
    p = model(3)
    offsets = [1e16, 1.0, -1e16]
    p.o = inf(sigma(p.x + offsets))
    CHECK.assertEqual(p.o.constant, 1)
    np.testing.assert_array_equal(p.C, [1, 1, 1])


def test_theta_algebra_preserves_parametric_constraint_signs():
    """
    Mixed theta constraints retain exact coefficients and RHS signs.
    """
    p = model(3)
    p.t = T(p.i, _=(0, 2))
    bound = 7
    p.c = p.k * p.x + p.t <= bound
    np.testing.assert_array_equal(p.A, np.diag([1, 2, 3]))
    np.testing.assert_array_equal(p.B, [7, 7, 7])
    np.testing.assert_array_equal(p.F, -np.eye(3))


def test_foreign_owners_are_rejected_before_objective_registration():
    """Native columns cannot conceal variables belonging to another program."""
    first, second = model(2), model(2)
    with CHECK.assertRaisesRegex(
        ValueError,
        "another program|Register variables",
    ):
        first.o = inf(sigma(first.x + second.x))
    CHECK.assertEqual(first.objectives, [])


def test_native_boundary_preserves_integer_coefficients_and_checks_overflow():
    """Native integers never narrow through the public P float adapter."""
    native = import_module("gana._native")
    p = model(2)
    variables = native.AffineRows.variables(
        p.x._symbol_storage.positions.handle,
    )
    coefficient = 2**120 + 1
    weights = native.AffineRows.constants([coefficient])
    result = weights.combine(variables, [], [0], "mul")
    CHECK.assertEqual(result.coefficients(1), [coefficient])
    copied = native.AffineRows(result.export())
    CHECK.assertEqual(
        copied.sum_all().matrix(0),
        [(0, coefficient), (1, coefficient)],
    )
    with CHECK.assertRaises(OverflowError):
        native.AffineRows.constants([2**140])
    with CHECK.assertRaises(OverflowError):
        native.AffineRows.constants([1024]).combine(result, [], [0], "mul")


def test_invalid_native_row_requests_leave_the_batch_unchanged():
    """Bad offsets and groups cannot publish a partial replacement."""
    native = import_module("gana._native")
    rows = native.AffineRows.constants([1, 2])
    with CHECK.assertRaises(ValueError):
        rows.with_offsets([3])
    with CHECK.assertRaises(IndexError):
        rows.sum_groups([[2]])
    with CHECK.assertRaises(IndexError):
        rows.sum_terms([[2]])
    CHECK.assertEqual(rows.offsets(), [1, 2])


def test_repeated_variable_axis_retains_legacy_default_position():
    """A repeated V axis still defaults to its first occurrence."""
    p = Prg()
    p.i = I(size=2)
    p.x = V(p.i, p.i)
    bound = 4
    p.c = sigma(p.x, p.i) <= bound
    np.testing.assert_array_equal(p.A, [[1, 0, 1, 0], [0, 1, 0, 1]])
