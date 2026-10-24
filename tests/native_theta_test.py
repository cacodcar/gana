"""Independent algebra, ownership and compatibility checks for native theta."""

import gc
import operator
import weakref
from copy import deepcopy
from importlib import import_module
from unittest import TestCase

import numpy as np
import pytest

from gana import I, P, Prg, T, V, inf, sigma, sup
from gana.backends.native.algebra import NativeRows
from gana.storage.parameters import NATIVE

CHECK = TestCase()
ROW_BOUND = 11
MIXED_BOUND = 7
REDUCED_BOUND = 17
COPY_BOUND = 4
pytestmark = pytest.mark.skipif(not NATIVE, reason="requires native theta")


def model(size=4):
    """Use overlapping V/T column numbers and distinct interval endpoints."""
    p = Prg()
    p.i = I(size=size)
    p.x = V(p.i, mutable=True)
    p.t = T(p.i, _=[(n - 2, n + 3) for n in range(size)], mutable=True)
    return p


def assert_lazy(p, expression):
    """Check numerical exports did not allocate scalar symbolic state."""
    CHECK.assertIsInstance(expression, NativeRows)
    CHECK.assertNotIn("_legacy_cache", expression.__dict__)
    CHECK.assertEqual(p.x._symbol_storage.states, {})
    CHECK.assertEqual(p.t._symbol_storage.states, {})


@pytest.mark.parametrize("sign", [-1, 1])
def test_mixed_rows_keep_independent_columns(sign):
    """A and F must never collide even when both symbols use column zero."""
    p = model()
    expression = 2 * (p.x + p.t) + sign * (p.x - p.t) + 3
    p.c = expression <= ROW_BOUND
    np.testing.assert_array_equal(p.A, (2 + sign) * np.eye(4))
    np.testing.assert_array_equal(p.A_sparse.toarray(), p.A)
    np.testing.assert_array_equal(p.F, -(2 - sign) * np.eye(4))
    np.testing.assert_array_equal(p.B, [8] * 4)
    assert_lazy(p, expression)
    CHECK.assertNotIn("_legacy_cache", p.c.__dict__)


@pytest.mark.parametrize("operation", [operator.add, operator.sub])
def test_theta_left_and_repeated_terms(operation):
    """Normalization preserves repeated RHS term order, signs and columns."""
    p = model()
    expression = operation(p.t, 3 * (p.x + p.t))
    p.c = expression <= MIXED_BOUND
    sign = 1 if operation is operator.add else -1
    np.testing.assert_array_equal(p.A, 3 * sign * np.eye(4))
    np.testing.assert_array_equal(p.F, -(1 + 3 * sign) * np.eye(4))
    np.testing.assert_array_equal(p.B, [7] * 4)
    assert_lazy(p, expression)
    # Deferred compatibility must produce the same complete matrices.
    list(p.c)
    np.testing.assert_array_equal(p.A, 3 * sign * np.eye(4))
    np.testing.assert_array_equal(p.F, -(1 + 3 * sign) * np.eye(4))


@pytest.mark.parametrize("left", [True, False])
def test_theta_only_constraints_and_cancellation(left):
    """Pure theta rows retain unused variable columns and explicit zeros."""
    p = model()
    expression = 2 - p.t if left else p.t - 2
    p.c = expression <= 0
    p.cancel = p.t - p.t == 0
    expected = (1 if left else -1) * np.eye(4)
    np.testing.assert_array_equal(p.A, np.zeros((8, 4)))
    np.testing.assert_array_equal(p.F, np.vstack((expected, np.zeros((4, 4)))))
    np.testing.assert_array_equal(p.B, [-2 if left else 2] * 4 + [0] * 4)
    assert_lazy(p, expression)


@pytest.mark.parametrize("axis", [0, 1, None])
def test_theta_reduction_and_selection(axis):
    """Coordinate arithmetic checks reversed selections and sums."""
    p = Prg()
    p.i, p.j = I(size=2), I(size=3)
    p.x, p.t = V(p.i, p.j), T(p.i, p.j, _=(-5, 9))
    axes = (p.i[::-1], p.j[::-1])
    source = (p.x - p.t + 2)(*axes)
    expression = (
        sigma(source) if axis is None else sigma(source, axes[axis], axis)
    )
    p.c = expression <= REDUCED_BOUND
    groups = (
        [[5, 4, 3, 2, 1, 0]]
        if axis is None
        else (
            [[5, 2], [4, 1], [3, 0]] if axis == 0 else [[5, 4, 3], [2, 1, 0]]
        )
    )
    expected = np.zeros((len(groups), 6))
    for row, columns in enumerate(groups):
        expected[row, columns] = 1
    np.testing.assert_array_equal(p.A, expected)
    np.testing.assert_array_equal(p.F, expected)
    np.testing.assert_array_equal(
        p.B,
        [17 - 2 * len(group) for group in groups],
    )
    assert_lazy(p, source)
    assert_lazy(p, expression)


def test_theta_broadcast_and_membership_snapshot():
    """A shorter theta repeats consecutively and later growth adds no terms."""
    p = model()
    selected = p.t(p.i[::2])
    expression = p.x + selected
    p.j = I("extra")
    p.t = T(p.j, _=(20, 30))
    p.c = expression <= 0
    expected = np.zeros((4, 5))
    expected[[0, 1], 0] = -1
    expected[[2, 3], 2] = -1
    np.testing.assert_array_equal(p.F, expected)
    assert_lazy(p, expression)
    list(p.c)
    np.testing.assert_array_equal(p.F, expected)


def test_growing_theta_keeps_public_operand_identity():
    """Compiled membership freezes while the exposed operand stays original."""
    p = model()
    expression = p.t + 2
    p.j = I("extra")
    p.t = T(p.j, _=(20, 30))
    p.c = expression <= 0
    expected = np.hstack((-np.eye(4), np.zeros((4, 1))))
    np.testing.assert_array_equal(p.F, expected)
    CHECK.assertIs(expression.two, p.t)
    CHECK.assertEqual(len(expression), 4)
    np.testing.assert_array_equal(p.F, expected)


@pytest.mark.parametrize("expose", [str, list])
def test_exposed_expression_binds_theta_at_registration(expose):
    """Reading F before a zero-bound constraint must still bind RHS columns."""
    p = model()
    expression = p.x + p.t
    expose(expression)
    p.c = expression <= 0
    np.testing.assert_array_equal(p.A, np.eye(4))
    np.testing.assert_array_equal(p.F, -np.eye(4))
    np.testing.assert_array_equal(p.B, [0] * 4)


@pytest.mark.parametrize("operation", [operator.add, operator.sub])
def test_theta_normalization_keeps_output_domain(operation):
    """Equal-sized distinct axes follow the same operand order as legacy F."""
    p = model()
    p.j = I("a", "b", "c", "d")
    p.s = T(p.j, _=(-2, 6))
    expression = operation(p.t, p.s)
    axis = p.j if operation is operator.add else p.i
    p.c = expression(axis[1::2]) <= 0
    expected = np.zeros((2, 8))
    expected[[0, 1], [1, 3]] = -1
    expected[[0, 1], [5, 7]] = -1 if operation is operator.add else 1
    np.testing.assert_array_equal(p.F, expected)
    assert_lazy(p, expression)
    list(p.c)
    np.testing.assert_array_equal(p.F, expected)


def test_registered_transforms_keep_bounds_and_names():
    """Direct T scaling creates its owner; subsequent F scaling keeps it."""
    p = model()
    p.negative = -2 * p.t
    before = p.negative._validated_bounds()
    expression = 3 * (p.x + p.negative)
    p.c = expression <= 0
    np.testing.assert_array_equal(
        p.F,
        np.hstack((np.zeros((4, 4)), -3 * np.eye(4))),
    )
    CHECK.assertEqual(p.negative._validated_bounds(), before)
    CHECK.assertEqual(str(p.negative), "-2*t")
    assert_lazy(p, expression)
    CHECK.assertNotIn("+ -", str(expression))
    CHECK.assertEqual(p.negative._validated_bounds(), before)


@pytest.mark.parametrize("compose", [inf, sup])
@pytest.mark.parametrize("cancel", [False, True])
def test_theta_objectives_remain_rejected(compose, cancel):
    """Even cancelled theta dependence keeps the existing objective rule."""
    p = model()
    expression = p.t - p.t if cancel else p.x + p.t
    with pytest.raises(ValueError, match="Theta-dependent objectives"):
        compose(sigma(expression))
    CHECK.assertEqual(p.n_objectives, 0)
    assert_lazy(p, expression)


def test_foreign_theta_is_rejected_before_registration():
    """A registered theta in another program must not acquire local links."""
    p, foreign = model(), model()
    expression = p.x + foreign.t
    before = (tuple(p.names), p.n_constraints)
    with pytest.raises(ValueError, match="another program"):
        p.c = expression <= 0
    CHECK.assertEqual((tuple(p.names), p.n_constraints), before)
    CHECK.assertEqual(
        p.x._symbol_storage.__dict__.get("constraint_links", []),
        [],
    )


@pytest.mark.parametrize("expose", [False, True])
def test_copy_and_mutable_compatibility_rows(expose):
    """Deepcopy keeps bound owners; exposed row coefficient lists stay live."""
    p = model()
    p.c = p.x + p.t <= COPY_BOUND
    if expose:
        list(p.c)
    restored = deepcopy(p)
    np.testing.assert_array_equal(restored.F, -np.eye(4))
    row = restored.c[1]
    row.function.F[0] = 7
    expected = -np.eye(4)
    expected[1, 1] = 7
    np.testing.assert_array_equal(restored.F, expected)
    np.testing.assert_array_equal(p.F, -np.eye(4))
    CHECK.assertIs(row.function._theta_terms[0][0], restored.t)


def test_expression_keeps_theta_owner_alive():
    """An expression owns its intervals and releases them with the graph."""
    p = model()
    expression = p.x + p.t
    reference = weakref.ref(p.t)
    del p
    gc.collect()
    CHECK.assertIsNotNone(reference())
    del expression
    gc.collect()
    CHECK.assertIsNone(reference())


def test_parameter_capture_with_theta():
    """Later numeric writes do not rewrite mixed theta coefficients."""
    p = model()
    p.k = P(p.i, _=[2, 3, 4, 5], mutable=True)
    expression = p.k * (p.x - p.t)
    p.k._[:] = [9] * 4
    p.c = expression <= 0
    np.testing.assert_array_equal(p.A, np.diag([2, 3, 4, 5]))
    np.testing.assert_array_equal(p.F, np.diag([2, 3, 4, 5]))
    assert_lazy(p, expression)


@pytest.mark.parametrize("mixed", [False, True])
def test_empty_theta_preserves_compatibility_error(mixed):
    """Empty T arithmetic keeps the established error at row construction."""
    p = model()
    left = p.x if mixed else p.t
    with pytest.raises(IndexError, match="list index out of range"):
        left(p.i[:0]) + p.t(p.i[:0])


def test_sparse_projection_validates_owner_masks():
    """Malformed native masks fail instead of mixing independent columns."""
    native = import_module("gana._native")
    batch = native.AffineRows([([(1, 0, 0)], [2], 0)])
    with pytest.raises(ValueError, match="row counts"):
        native.SparseRows([batch], 1, owners=[])
    with pytest.raises(IndexError, match="owner position"):
        native.SparseRows([batch], 1, owners=[[True]])
    CHECK.assertEqual(
        native.SparseRows([batch], 0, owners=[[True, False]]).dense(),
        [[]],
    )
    CHECK.assertEqual(
        native.SparseRows(
            [batch],
            1,
            owners=[[False, True]],
            negate=True,
        ).dense(),
        [[-2]],
    )
