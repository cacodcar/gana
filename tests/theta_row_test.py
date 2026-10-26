"""Ownership, indexing and numerical contracts for anonymous theta rows."""

import gc
import operator
import weakref
from copy import deepcopy
from unittest import TestCase

import numpy as np
import pytest

from gana import I, Prg, T, V

CHECK = TestCase()
ROW_BOUND = 10
MULTI_BOUND = 20
BROADCAST_BOUND = 7


def model():
    """Use distinct intervals so a wrong coordinate cannot pass unnoticed."""
    program = Prg()
    program.i = I(size=3)
    program.x = V(program.i)
    program.t = T(program.i, _=[(1, 3), (4, 7), (-5, -2)])
    return program


@pytest.mark.parametrize("registered", [False, True])
@pytest.mark.parametrize("position", [0, 1, 2])
@pytest.mark.parametrize("operation", ["shift", "scale", "divide", "negate"])
def test_nested_row_arithmetic(registered, position, operation):
    """Reusing a scalar F keeps its transformed owner and exact column."""
    p = model()
    owner = -2 * p.t
    expression = p.x + owner
    row = expression[position]
    if registered:
        p.transformed = owner
    operations = {
        "shift": (lambda f: f + 4, 1, 4),
        "scale": (lambda f: 3 * f, 3, 0),
        "divide": (lambda f: f / 2, 0.5, 0),
        "negate": (operator.neg, -1, 0),
    }
    apply, coefficient, constant = operations[operation]
    p.row = apply(row) <= ROW_BOUND
    expected_a = np.zeros((1, 3))
    expected_a[0, position] = coefficient
    expected_f = np.zeros((1, 6))
    expected_f[0, 3 + position] = -coefficient
    np.testing.assert_array_equal(p.A, expected_a)
    np.testing.assert_array_equal(p.F, expected_f)
    np.testing.assert_array_equal(p.B, [10 - constant])
    CHECK.assertEqual(p.n_thetas, 6)
    CHECK.assertIs(p.theta_sets[1], owner)


@pytest.mark.parametrize("registered", [False, True])
@pytest.mark.parametrize("position", [0, 1, 2])
def test_exposed_theta_operand(registered, position):
    """A theta read from an expression row retains ordinary T operations."""
    p = model()
    owner = -2 * p.t
    row = (p.x + owner)[position].two
    label, latex = str(row), row.latex()
    expected = [(-6, -2), (-14, -8), (4, 10)][position]
    if registered:
        p.transformed = owner
    CHECK.assertIsInstance(row, T)
    CHECK.assertIs(row._owner_root, owner)
    CHECK.assertEqual(row._validated_bounds(), [expected])
    CHECK.assertEqual(list(row.map), [list(owner.map)[position]])
    CHECK.assertEqual(len(row), 1)
    CHECK.assertEqual(str(row), label)
    CHECK.assertEqual(row.latex(), latex)
    doubled = row * -2
    CHECK.assertIsNot(doubled._owner_root, owner)
    CHECK.assertEqual(
        doubled._validated_bounds(),
        [(-2 * expected[1], -2 * expected[0])],
    )
    p.row = p.x[position] + row + 4 <= ROW_BOUND
    expected_f = np.zeros((1, 6))
    expected_f[0, 3 + position] = -1
    np.testing.assert_array_equal(p.F, expected_f)
    CHECK.assertEqual(p.n_thetas, 6)


def test_reversed_multidimensional_anonymous_selection():
    """Selected rows bind original coordinates, even across two axes."""
    p = Prg()
    p.i, p.j = I(size=2), I(size=3)
    p.x = V(p.i, p.j)
    owner = T(p.i, p.j, _=[(n, n + 1) for n in range(6)])
    selected = owner(p.i[::-1], p.j[::-2])
    expression = p.x(p.i[::-1], p.j[::-2]) + selected
    p.row = 2 * expression + 3 <= MULTI_BOUND
    columns = [5, 3, 2, 0]
    np.testing.assert_array_equal(p.A, 2 * np.eye(6)[columns])
    np.testing.assert_array_equal(p.F, -2 * np.eye(6)[columns])
    np.testing.assert_array_equal(p.B, [17] * 4)
    CHECK.assertIs(p.theta_sets[0], owner)
    CHECK.assertEqual(
        owner._validated_bounds(),
        [(n, n + 1) for n in range(6)],
    )


@pytest.mark.parametrize("size", [1, 2])
def test_anonymous_broadcast(size):
    """Broadcast references reuse their owner and repeat consecutive rows."""
    p = Prg()
    p.i = I(size=4)
    p.x = V(p.i)
    owner = T(_=[(n, n + 2) for n in range(size)])
    expression = p.x + owner
    p.row = expression <= BROADCAST_BOUND
    np.testing.assert_array_equal(
        p.F,
        -np.repeat(np.eye(size), 4 // size, axis=0),
    )
    CHECK.assertEqual(p.n_thetas, size)
    CHECK.assertTrue(all(row.two._owner_root is owner for row in expression))


def test_row_keeps_owner_alive_and_releases_it():
    """A retained row owns its bounds; dropping it releases the whole graph."""
    p = model()
    owner = -2 * p.t
    reference = weakref.ref(owner)
    expression = p.x + owner
    row = expression[1].two
    del expression, owner
    gc.collect()
    CHECK.assertIsNotNone(reference())
    CHECK.assertEqual(row._validated_bounds(), [(-14, -8)])
    del row
    gc.collect()
    CHECK.assertIsNone(reference())


def test_foreign_row_rejected_atomically():
    """Binding an owner elsewhere must not partially register a constraint."""
    p = model()
    owner = -2 * p.t
    row = (p.x + owner)[1]
    foreign = Prg()
    foreign.transformed = owner
    before = (tuple(p.names), p.n_thetas, p.n_constraints)
    with pytest.raises(ValueError, match="another program"):
        p.row = row <= ROW_BOUND
    CHECK.assertEqual((tuple(p.names), p.n_thetas, p.n_constraints), before)


def test_anonymous_row_copy():
    """Copying the reference graph retains an owner and selected bounds."""
    p = model()
    row = (p.x + (-2 * p.t))[1].two
    restored = deepcopy(row)
    CHECK.assertEqual(str(restored), str(row))
    CHECK.assertEqual(restored._validated_bounds(), [(-14, -8)])
    CHECK.assertEqual((restored / 2)._validated_bounds(), [(-7, -4)])


def test_variable_coordinate_is_atomic():
    """An indexed variable in a coordinate must not expand into its members."""
    p = model()
    coordinate = p.x[0]
    p.y = V(coordinate, p.i)
    owner = T(coordinate, p.i, _=[(1, 2), (3, 4), (5, 6)])
    expression = p.y + owner
    row = expression[1].two
    CHECK.assertIs(row.index[0][0], coordinate)
    CHECK.assertEqual(row._validated_bounds(), [(3, 4)])
    p.row = expression <= ROW_BOUND
    np.testing.assert_array_equal(
        p.F,
        np.hstack((np.zeros((3, 3)), -np.eye(3))),
    )
