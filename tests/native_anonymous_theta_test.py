"""Late theta registration preserves algebra, ownership and public reads."""

import gc
import pickle
import weakref
from copy import deepcopy
from importlib import import_module
from unittest import TestCase

import numpy as np
import pytest

from gana import I, Prg, T, V, inf, sigma
from gana.backends.native.algebra import NativeRows

CHECK = TestCase()
ROW_BOUND = 11
SCALAR_BOUND = 9


def model():
    """Reserve earlier theta columns so premature numbering is observable."""
    p = Prg()
    p.i = I(size=4)
    p.x = V(p.i)
    p.earlier = T(_=(-7, 8))
    return p, T(p.i, _=(-2, 5), mutable=True)


@pytest.mark.parametrize("expose", [None, str, list])
@pytest.mark.parametrize("explicit", [False, True])
def test_anonymous_registration_and_replay(expose, explicit):
    """Reading either side of registration must retain the final columns."""
    p, theta = model()
    expression = 2 * (p.x - theta) + 3
    CHECK.assertIsInstance(expression, NativeRows)
    CHECK.assertFalse(theta.birthed)
    CHECK.assertEqual(p.n_thetas, 1)
    CHECK.assertEqual(theta._, [(-2, 5)] * 4)
    if expose:
        expose(expression)
    if explicit:
        p.named = theta
    p.c = expression <= ROW_BOUND
    expected = np.hstack((np.zeros((4, 1)), 2 * np.eye(4)))
    np.testing.assert_array_equal(p.A_sparse.toarray(), 2 * np.eye(4))
    np.testing.assert_array_equal(p.F, expected)
    np.testing.assert_array_equal(p.B, [8] * 4)
    CHECK.assertEqual(p.n_theta_sets, 2)
    CHECK.assertIs(p.theta_sets[1], theta)
    CHECK.assertEqual(
        p.names[-2:],
        ["named", "c"] if explicit else ["c", "θ1"],
    )
    if expose is None:
        CHECK.assertNotIn("_legacy_cache", p.c.__dict__)
        CHECK.assertEqual(theta._symbol_storage.states, {})
    list(p.c)
    np.testing.assert_array_equal(p.F, expected)


def test_shared_anonymous_owner_and_mixed_registration():
    """One interval reused before and after registration has one column set."""
    p, theta = model()
    first = p.x + theta
    second = p.x - theta
    CHECK.assertIs(first._native_owners[1], second._native_owners[1])
    p.named = theta
    p.c = first - (p.x + theta) + second <= 0
    np.testing.assert_array_equal(p.A, np.eye(4))
    np.testing.assert_array_equal(
        p.F,
        np.hstack((np.zeros((4, 1)), np.eye(4))),
    )
    CHECK.assertEqual(p.n_theta_sets, 2)


@pytest.mark.parametrize("reduced", [False, True])
def test_anonymous_selection_and_later_growth(reduced):
    """Frozen reversed coordinates survive owner growth and reductions."""
    p, theta = model()
    axis = p.i[::-2]
    source = p.x(axis) - theta(axis)
    expression = sigma(source) if reduced else source
    p.named = theta
    p.j = I("extra")
    p.named = T(p.j, _=(10, 20))
    p.c = expression <= 0
    expected = np.zeros((1 if reduced else 2, 6))
    expected[0, 4] = 1
    expected[0 if reduced else 1, 2] = 1
    np.testing.assert_array_equal(p.F, expected)
    list(p.c)
    np.testing.assert_array_equal(p.F, expected)


def test_latest_anonymous_bounds_and_independent_transform():
    """Binding reads current declaration bounds; direct scaling owns a copy."""
    p, theta = model()
    transformed = -2 * theta
    expression = p.x - theta + transformed
    theta._[0] = (-10, 12)
    p.c = expression <= 0
    CHECK.assertEqual(theta._validated_bounds()[0], (-10, 12))
    CHECK.assertEqual(transformed._validated_bounds(), [(-10, 4)] * 4)
    expected = np.hstack((np.zeros((4, 1)), np.eye(4), -np.eye(4)))
    np.testing.assert_array_equal(p.F, expected)
    CHECK.assertEqual(p.n_theta_sets, 3)


@pytest.mark.parametrize("invalid", ["foreign", "bounds", "coordinate"])
def test_rejected_declarations_do_not_register_constraints(invalid):
    """Validate every owner before changing any registry or variable links."""
    p, theta = model()
    other = T(p.i, _=(1, 3))
    expression = p.x + theta + other
    if invalid == "foreign":
        foreign = Prg()
        foreign.t = other
    elif invalid == "bounds":
        other._[0] = (8, -1)
    else:
        other.map.pop(next(iter(other.map)))
        other._.pop(0)
    with pytest.raises((ValueError, KeyError)):
        p.c = expression <= 0
    CHECK.assertEqual(p.n_thetas, 1)
    CHECK.assertEqual(p.n_constraints, 0)
    CHECK.assertFalse(theta.birthed)
    CHECK.assertNotIn("constraint_links", p.x._symbol_storage.__dict__)


@pytest.mark.parametrize("registered", [False, True])
@pytest.mark.parametrize("clone", [deepcopy, pickle.loads])
def test_deferred_graph_copy_and_serialization(registered, clone):
    """Restored graphs share their restored owner, including resolved maps."""
    p, theta = model()
    expression = p.x - theta
    if registered:
        p.c = expression <= 0
        _ = p.F
    graph = (p, theta, expression)
    restored = (
        clone(pickle.dumps(graph)) if clone is pickle.loads else clone(graph)
    )
    q, copied_theta, copied_expression = restored
    if not registered:
        q.c = copied_expression <= 0
    np.testing.assert_array_equal(
        q.F,
        np.hstack((np.zeros((4, 1)), np.eye(4))),
    )
    CHECK.assertIs(q.theta_sets[1], copied_theta)
    CHECK.assertIsNot(copied_theta, theta)
    list(q.c)
    np.testing.assert_array_equal(
        q.F,
        np.hstack((np.zeros((4, 1)), np.eye(4))),
    )


def test_anonymous_graph_releases_its_owner():
    """The coordinate reference retains no graph after its last user dies."""
    p, theta = model()
    expression = p.x - theta
    reference = weakref.ref(theta)
    del theta, p
    gc.collect()
    CHECK.assertIsNotNone(reference())
    del expression
    gc.collect()
    CHECK.assertIsNone(reference())


def test_named_scalar_expression_defers_registration():
    """Naming a function captures algebra without consuming theta columns."""
    p = Prg()
    theta = T(_=(-2, 5))
    p.expense = theta + 2
    CHECK.assertEqual(p.n_thetas, 0)
    CHECK.assertFalse(theta.birthed)
    with pytest.raises(ValueError, match="Theta-dependent objectives"):
        inf(p.expense)
    p.c = p.expense <= SCALAR_BOUND
    np.testing.assert_array_equal(p.F, [[-1]])
    np.testing.assert_array_equal(p.B, [7])
    CHECK.assertEqual(p.n_thetas, 1)


def test_distinct_anonymous_owners_preserve_normalized_order():
    """Theta-left addition normalizes owner order exactly like legacy F."""
    p, theta = model()
    other = T(p.i, _=(3, 6))
    expression = theta + other
    p.c = expression <= 0
    CHECK.assertIs(p.theta_sets[1], other)
    CHECK.assertIs(p.theta_sets[2], theta)
    np.testing.assert_array_equal(
        p.F,
        np.hstack((np.zeros((4, 1)), -np.eye(4), -np.eye(4))),
    )


def test_late_columns_validate_python_boundary():
    """Incomplete mapping tables cannot silently assign incorrect columns."""
    native = import_module("gana._native")
    batch = native.AffineRows([([(0, 1, 0)], [2], 0)])
    table = native.MemberTable([[0], [1]], [3, 2], [None, None])
    CHECK.assertEqual(
        native.SparseRows([batch], 4, column_tables=[[table]]).dense(),
        [[0, 0, 2, 0]],
    )
    with pytest.raises(ValueError, match="row counts"):
        native.SparseRows([batch], 4, column_tables=[])
    with pytest.raises(IndexError, match="owner position"):
        native.SparseRows([batch], 4, column_tables=[[]])
    with pytest.raises(IndexError, match="owner position"):
        native.SparseRows([batch], 4, column_tables=[[table.take([0])]])


@pytest.mark.parametrize("occupied", [False, True])
def test_generated_theta_names_reject_collisions_atomically(occupied):
    """Reserve automatic theta names before changing any public registry."""
    p, theta = model()
    if occupied:
        p.θ1 = V()
    name = "c" if occupied else "θ1"
    names = p.names.copy()
    with pytest.raises(ValueError, match=r"θ1.*already registered"):
        setattr(p, name, p.x - theta <= 0)
    CHECK.assertEqual(p.names, names)
    CHECK.assertEqual(p.n_constraints, 0)
    CHECK.assertEqual(p.n_thetas, 1)
    CHECK.assertFalse(theta.birthed)
