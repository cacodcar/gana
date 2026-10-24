"""
Constraint ownership, exact compilation and compatibility regression cases.
"""

from copy import deepcopy
from importlib import import_module
from unittest import TestCase

import numpy as np
import pytest

from gana import I, P, Prg, T, V, inf, sigma
from gana.backends.native.constraints import NativeConstraint
from gana.sets.constraint import C
from gana.storage.parameters import NATIVE

CHECK = TestCase()


def model(size=4):
    """Register fresh owners without instantiating symbolic member wrappers."""
    p = Prg()
    p.i = I(size=size)
    p.x = V(p.i, mutable=True)
    p.k = P(p.i, _=list(range(1, size + 1)), mutable=True)
    return p


def test_sparse_and_dense_independent_coefficients():
    """Sparse and dense outputs retain repeated columns and numeric offsets."""
    p = model()
    p.c = p.k * p.x + p.x - 2 * p.x + 3 <= [10, 20, 30, 40]
    np.testing.assert_array_equal(p.A, np.diag([0, 1, 2, 3]))
    np.testing.assert_array_equal(p.A_sparse.toarray(), np.diag([0, 1, 2, 3]))
    CHECK.assertEqual(p.B, [7, 17, 27, 37])
    if NATIVE:
        CHECK.assertIsInstance(p.c, NativeConstraint)
        CHECK.assertEqual(p.x._symbol_storage.states, {})
        CHECK.assertNotIn("_legacy_cache", p.c.__dict__)


def test_constraint_order_and_nonnegativity():
    """
    Interleaved registration exports inequalities, equalities, then bounds.
    """
    p = model(2)
    p.eq = 2 * p.x == [4, 6]
    p.nn = p.x >= 0
    p.upper = 3 * p.x <= [9, 12]
    expected = [[3, 0], [0, 3], [2, 0], [0, 2], [-1, 0], [0, -1]]
    CHECK.assertEqual(p.A, expected)
    np.testing.assert_array_equal(p.A_sparse.toarray(), expected)
    CHECK.assertEqual(p.B, [9, 12, 4, 6, 0, 0])
    CHECK.assertEqual(p.cons(n=True), [4, 5, 0, 1, 2, 3])
    CHECK.assertIs(p.constraints[0].parent, p.eq)


def test_held_metadata_and_replacement():
    """
    Retained cons_by lists observe replacement without duplicate references.
    """
    p = model(2)
    held = p.x[0]
    links = held.cons_by
    first_bound, second_bound, replacement_bound = 4, 6, 10
    p.first = p.k * p.x + p.x <= first_bound
    p.second = 3 * p.x == second_bound
    old = p.first[0]
    CHECK.assertEqual([id(row) for row in links], [id(old), id(p.second[0])])
    p.first.categorize("Capacity")
    p.first = 4 * p.x(p.i[:1]) <= replacement_bound
    CHECK.assertEqual(p.first.category, "Capacity")
    CHECK.assertFalse(any(row is old for row in held.cons_by))
    CHECK.assertEqual(len(held.cons_by), 2)
    CHECK.assertEqual(len(p.x[1].cons_by), 1)
    for member in p.x:
        for position, row in enumerate(member.cons_by):
            CHECK.assertEqual(row.cons_by_pos[member], position)
    CHECK.assertEqual(p.A, [[4, 0], [3, 0], [0, 3]])


def test_deferred_metadata_uses_original_rows():
    """First metadata access creates stable identities with correct parents."""
    p = model(2)
    bound = 7
    p.c = p.x + p.x <= bound
    p.c.categorize("Capacity")
    held = p.x[0]
    CHECK.assertEqual(held.cons_by, [p.c[0]])
    CHECK.assertIs(p.c[0].parent, p.c)
    CHECK.assertIs(p.constraints[0], p.c[0])
    CHECK.assertEqual(p.c[0].category, "Capacity")
    CHECK.assertEqual(p.c[0].cons_by_pos[held], 0)


def test_pending_links_keep_insertion_order_across_owners():
    """
    Resolving overlapping owners cannot register newer rows ahead of older
    ones.
    """
    p = model(2)
    p.y = V(p.i)
    first_bound, middle_bound, last_bound = 8, 9, 10
    p.first = 2 * p.y <= first_bound
    p.middle = p.x + p.y <= middle_bound
    p.last = 3 * p.x <= last_bound
    xlinks = p.x[0].cons_by
    ylinks = p.y[0].cons_by
    CHECK.assertEqual(
        [id(row) for row in xlinks],
        [id(p.middle[0]), id(p.last[0])],
    )
    CHECK.assertEqual(
        [id(row) for row in ylinks],
        [id(p.first[0]), id(p.middle[0])],
    )


def test_constructor_category_and_explicit_categorize():
    """Only categorize propagates root metadata to children, as in legacy C."""
    p = model(2)
    p.c = C(2 * p.x, leq=True, category="Root")
    CHECK.assertEqual(p.c.category, "Root")
    CHECK.assertEqual(p.c[0].category, "General")
    p.c.categorize("Shared")
    CHECK.assertEqual([row.category for row in p.c], ["Shared", "Shared"])


@pytest.mark.parametrize("expose_member", [False, True])
def test_reusing_registered_constraint_preserves_row_links(expose_member):
    """Repeated registration of the same C matches legacy row identity."""
    p = model(2)
    if expose_member:
        CHECK.assertEqual(p.x[0].cons_by, [])
    bound = 8
    p.first = 2 * p.x <= bound
    p.alias = p.first
    CHECK.assertEqual(p.A, [[2, 0], [0, 2], [2, 0], [0, 2]])
    CHECK.assertEqual(
        [id(row) for row in p.x[0].cons_by],
        [id(p.first[0])] * 2,
    )


def test_membership_and_numeric_capture_after_growth():
    """
    Existing constraints retain captured data while unused columns expand.
    """
    p = model(2)
    bound = 8
    p.c = p.k * p.x <= bound
    p.k._[:] = [9, 9]
    p.j = I("new")
    p.x = V(p.j)
    CHECK.assertEqual(p.A, [[1, 0, 0], [0, 2, 0]])
    np.testing.assert_array_equal(p.A_sparse.toarray(), p.A)
    CHECK.assertEqual(p.x[2].cons_by, [])


@pytest.mark.parametrize("large", [2**60 + 1, 2**127 - 1, 2**130])
def test_large_values_preserve_public_parameter_conversion(large):
    """The public P adapter converts input numbers to float before algebra."""
    p = model(1)
    p.c = large * p.x + p.x <= large
    CHECK.assertEqual(p.A, [[float(large) + 1]])
    CHECK.assertEqual(p.B, [float(large)])


def test_mixed_theta_and_native_rows():
    """Theta constraints retain their established RHS signs and ordering."""
    p = model(2)
    p.t = T(p.i, _=(0, 10))
    bound = 5
    p.c = p.k * p.x <= bound
    p.parametric = 3 * p.x <= p.t
    np.testing.assert_array_equal(
        p.A_sparse.toarray(),
        [[1, 0], [0, 2], [3, 0], [0, 3]],
    )
    CHECK.assertEqual(p.B, [5, 5, 0, 0])
    CHECK.assertEqual(p.F, [[0, 0], [0, 0], [1, 0], [0, 1]])


def test_empty_sparse_shape():
    """An unconstrained model retains all unused columns in sparse output."""
    p = model()
    CHECK.assertEqual(p.A_sparse.shape, (0, 4))
    CHECK.assertEqual(p.A, [])
    CHECK.assertEqual(p.B, [])


def test_deepcopy_keeps_one_owner_graph():
    """
    Pending registrations restore against copied owners, not the originals.
    """
    p = model(2)
    bound = 8
    p.c = 2 * p.x <= bound
    p.o = inf(sigma(p.x))
    copied = deepcopy(p)
    CHECK.assertEqual(copied.A, [[2, 0], [0, 2]])
    CHECK.assertIs(copied.x[0].cons_by[0], copied.c[0])
    CHECK.assertIsNot(copied.c[0], p.c[0])
    CHECK.assertIs(copied.c[0].variables[0].parent, copied.x)


@pytest.mark.skipif(not NATIVE, reason="requires native sparse compiler")
def test_native_sparse_bounds_and_detached_exports():
    """
    Checked IDs prevent out-of-bounds writes; detached buffers are harmless.
    """
    native = import_module("gana._native")
    batch = native.AffineRows([([(0, 0, 3)], [2], -7)])
    with pytest.raises(IndexError):
        native.SparseRows([batch], 3)
    compiled = native.SparseRows([batch], 5)
    data, indices, indptr = compiled.parts()
    data[0], indices[0], indptr[0] = 99, 99, 99
    CHECK.assertEqual(compiled.dense(), [[0, 0, 0, 2, 0]])
    CHECK.assertEqual(compiled.rhs(), [7])
    CHECK.assertGreater(compiled.reserved_bytes, 0)


@pytest.mark.skipif(not NATIVE, reason="requires native sparse compiler")
def test_exact_native_integers_and_overflow():
    """
    Native inputs retain integer kinds and signal overflow for Python fallback.
    """
    native = import_module("gana._native")
    large = 2**120 + 1
    row = native.AffineRows([([(0, 0, 0), (0, 0, 0)], [large, 1], -large)])
    compiled = native.SparseRows([row], 1)
    CHECK.assertEqual(compiled.dense(), [[large + 1]])
    CHECK.assertEqual(compiled.rhs(), [large])
    overflow = native.AffineRows(
        [([(0, 0, 0), (0, 0, 0)], [2**127 - 1, 1], 0)],
    )
    with CHECK.assertRaises(OverflowError):
        native.SparseRows([overflow], 1)


def test_exposed_scalar_coefficients_remain_authoritative():
    """Editing compatibility rows cannot leave a stale native matrix in use."""
    p = model(2)
    bound = 4
    p.c = 2 * p.x <= bound
    p.c[0].function.A[0] = 9
    CHECK.assertEqual(p.A, [[9, 0], [0, 2]])
    np.testing.assert_array_equal(p.A_sparse.toarray(), p.A)
