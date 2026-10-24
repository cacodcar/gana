"""
Expression selection parity, native ownership and mutable row regressions.
"""

from copy import deepcopy
from gc import collect
from importlib import import_module
from unittest import TestCase
from weakref import ref

import numpy as np
import pytest

from gana import I, P, Prg, V, inf, sigma
from gana.backends.native.algebra import _LEGACY, NativeRows
from gana.sets.constraint import C
from gana.storage.parameters import NATIVE

CHECK = TestCase()


def grid():
    """Give each coordinate a distinct coefficient and global solver column."""
    p = Prg()
    p.i, p.j = I(size=3), I(size=4)
    p.x = V(p.i, p.j, mutable=True)
    p.k = P(p.i, p.j, _=list(range(1, 13)), mutable=True)
    return p


def assert_lazy(p, *expressions):
    """Check that native construction has not requested any scalar wrappers."""
    if NATIVE:
        CHECK.assertEqual(p.x._symbol_storage.states, {})
        for expression in expressions:
            CHECK.assertIsInstance(expression, NativeRows)
            CHECK.assertNotIn("_legacy_cache", expression.__dict__)


@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("grouped", [False, True])
def test_selected_affine_rows_keep_order_and_export(nested, grouped):
    """
    Select reversals and strides; check every exported sparse coefficient.
    """
    p = grid()
    source = p.k * p.x + 3
    if nested:
        source = source(p.i[::-1], p.j[::-1])
    key = (p.i[::2], p.j[::-2])
    selected = source(key) if grouped else source(*key)
    if not grouped:
        assert_lazy(p, source, selected)
    bound = 20
    p.c = selected <= bound
    columns = [3, 1, 11, 9]
    expected = np.zeros((4, 12))
    expected[np.arange(4), columns] = np.array(columns) + 1
    np.testing.assert_array_equal(p.A_sparse.toarray(), expected)
    np.testing.assert_array_equal(p.B, [17] * 4)
    p.o = inf(sigma(selected))
    np.testing.assert_array_equal(p.C, expected.sum(axis=0))
    CHECK.assertEqual(p.o.constant, 12)


@pytest.mark.parametrize("axis", [0, 1])
def test_selection_after_axis_reduction_remains_native(axis):
    """Reduced output coordinates select groups of original solver columns."""
    p = grid()
    reduced = sigma(p.k * p.x, (p.i, p.j)[axis], position=axis)
    remaining = (p.j, p.i)[axis]
    selected = reduced(remaining[::-2])
    assert_lazy(p, reduced, selected)
    p.o = inf(sigma(selected))
    expected = [
        n + 1
        if (n % 4 if axis == 0 else n // 4)
        in (range(4)[::-2] if axis == 0 else range(3)[::-2])
        else 0
        for n in range(12)
    ]
    np.testing.assert_array_equal(p.C, expected)


def test_selected_rows_capture_coefficients_and_frozen_membership():
    """Parameter edits and later variable growth cannot rewrite a selection."""
    p = grid()
    source = p.k * p.x
    selected = source(p.i[:1], p.j[::-1])
    p.k._[:] = [99] * 12
    p.extra = I("extra")
    p.x = V(p.extra, p.j)
    p.o = inf(sigma(selected))
    np.testing.assert_array_equal(p.C, [1, 2, 3, 4] + [0] * 12)


@pytest.mark.parametrize("edit_sibling", [False, True])
def test_source_row_edits_are_visible_to_existing_selections(edit_sibling):
    """
    Sharing compatibility rows cannot leave a stale native operand behind.
    """
    p = grid()
    source = p.k * p.x
    selected = source(p.i[:1], p.j[:1])
    exposed = source(p.i[:1], p.j[:1]) if edit_sibling else source
    exposed[0].A[0] = 17
    bound = 19
    p.c = 2 * selected <= bound
    expected = np.zeros((1, 12))
    expected[0, 0] = 34
    np.testing.assert_array_equal(p.A, expected)
    p.o = inf(selected)
    np.testing.assert_array_equal(p.C, [17] + [0] * 11)
    CHECK.assertIs(selected[0], source[0])


def test_direct_constraint_uses_exposed_shared_rows():
    """
    A previously registered direct constraint must respect later row edits.
    """
    p = grid()
    source = p.k * p.x
    selected = source(p.i[:1], p.j[:1])
    p.c = C(selected)
    source[0].A[0] = 23
    expected = np.zeros((1, 12))
    expected[0, 0] = 23
    np.testing.assert_array_equal(p.A_sparse.toarray(), expected)


@pytest.mark.parametrize("operation", ["select", "reduce", "scale"])
def test_selection_printing_and_row_identity_match_legacy(operation):
    """Compare exact plain/LaTeX output against independent legacy replay."""
    p, reference = grid(), grid()

    def build(program):
        """
        Construct the same public expression with or without native dispatch.
        """
        expression = program.k * program.x - 3
        selected = expression(program.i[::2], program.j[::-2])
        operations = {
            "select": lambda: selected,
            "reduce": lambda: sigma(selected),
            "scale": lambda: -2 * selected,
        }
        return operations[operation]()

    actual = build(p)
    token = _LEGACY.set(True)
    try:
        expected = build(reference)
    finally:
        _LEGACY.reset(token)
    CHECK.assertEqual(str(actual), str(expected))
    CHECK.assertEqual(actual.latex(), expected.latex())
    CHECK.assertEqual(actual.longname, expected.longname)
    CHECK.assertEqual([row.A for row in actual], [row.A for row in expected])
    CHECK.assertEqual([row.B for row in actual], [row.B for row in expected])
    CHECK.assertEqual(
        [str(row) for row in actual],
        [str(row) for row in expected],
    )


def test_named_selection_deepcopy_keeps_scalar_owner_identity():
    """
    Serialized selections restore registration and shared compatibility rows.
    """
    p = grid()
    p.expression = p.k * p.x
    p.selected = p.expression(p.i[:1], p.j[::-1])
    restored = deepcopy(p)
    CHECK.assertIs(restored.selected[0], restored.expression[3])
    CHECK.assertIs(restored.selected[0].variables[0], restored.x[3])
    CHECK.assertEqual(restored.selected[0].n, 12)
    CHECK.assertEqual(p.n_functions, 16)


@pytest.mark.parametrize("first", ["source", "left", "right", "derived"])
@pytest.mark.parametrize("reverse_registration", [False, True])
def test_overlapping_selection_numbers_follow_registration(
    first,
    reverse_registration,
):
    """Shared rows keep registration order regardless of first exposure."""
    p = Prg()
    p.i = I(size=4)
    p.x = V(p.i)
    source = 2 * p.x
    left, right = source(p.i[:2]), source(p.i[:2])
    collections = {"source": source, "left": left, "right": right}
    order = list(collections)
    if reverse_registration:
        order.reverse()
    for name in order:
        setattr(p, name, collections[name])
    derived = 3 * right
    collections["derived"] = derived
    # Trigger deferred replay through each possible branch of the graph.
    CHECK.assertEqual(
        collections[first][0].A,
        [6 if first == "derived" else 2],
    )
    expected = [4, 5, 6, 7] if reverse_registration else [6, 7, 2, 3]
    CHECK.assertEqual([row.n for row in source], expected)
    CHECK.assertEqual([row.n for row in left], expected[:2])
    CHECK.assertEqual([row.n for row in right], expected[:2])
    CHECK.assertIs(source[0], left[0])
    CHECK.assertIs(source[0], right[0])
    CHECK.assertEqual(p.n_functions, 8)


@pytest.mark.parametrize("edit_coefficients", [False, True])
def test_scalar_objective_retains_selection_aliases(edit_coefficients):
    """
    Objective coefficients remain shared after source or public list edits.
    """
    p = grid()
    source = p.k * p.x
    selected = source(p.i[:1], p.j[:1])
    p.o = inf(selected)
    coefficients = p.o.C if edit_coefficients else source[0].A
    coefficients[0] = 31
    np.testing.assert_array_equal(p.C, [31] + [0] * 11)
    CHECK.assertEqual(p.o.P, [0])


def test_empty_invalid_and_positional_selections_keep_public_behavior():
    """Empty calls retain identity; positional slices still return lists."""
    p = grid()
    source = p.k * p.x
    CHECK.assertIs(source(), source)
    CHECK.assertEqual(len(source(p.i[:0], p.j)), 0)
    with CHECK.assertRaisesRegex(ValueError, "output dimensions"):
        source(p.i)
    p.missing = I("missing")
    with CHECK.assertRaises(KeyError) as error:
        source(p.missing, p.j)
    CHECK.assertEqual(error.exception.args[0], (p.missing[0], p.j[0]))
    CHECK.assertIsInstance(source[1:3], list)
    CHECK.assertEqual(len(source[1:3]), 2)


def test_explicit_member_list_edits_change_selection_length():
    """A materialized selection keeps ordinary mutable collection behavior."""
    p = grid()
    source = p.k * p.x
    selected = source(p.i[:1], p.j[:2])
    selected._.pop()
    CHECK.assertEqual(len(selected), 1)
    p.o = inf(selected)
    np.testing.assert_array_equal(p.C, [1] + [0] * 11)
    CHECK.assertEqual(len(source), 12)


@pytest.mark.parametrize("nested", [False, True])
def test_source_list_edits_preserve_existing_selection_members(nested):
    """Selection membership survives deletion and replacement in its source."""
    p = grid()
    source = p.k * p.x
    selected = source(p.i[:1], p.j[:2])
    if nested:
        selected = selected(p.i[:1], p.j[:1])
    original = source[0]
    source._.pop(0)
    source._[0] = source._[1]
    CHECK.assertIs(selected[0], original)
    CHECK.assertEqual(selected[0].A, [1])


@pytest.mark.parametrize("edit_list", [False, True])
def test_derived_expression_captures_rows_before_later_edits(edit_list):
    """Deferred arithmetic captures shape and coefficients at construction."""
    p = grid()
    source = p.k * p.x
    selected = source(p.i[:1], p.j[:2])
    derived = 3 * selected + 5
    if edit_list:
        selected._.pop(0)
    else:
        source[0].A[0] = 17
    CHECK.assertEqual(len(derived), 2)
    CHECK.assertEqual([row.A for row in derived], [[3], [6]])
    CHECK.assertEqual([row.B for row in derived], [-5, -5])


@pytest.mark.skipif(not NATIVE, reason="requires native replay dependencies")
def test_discarded_native_selections_are_not_retained():
    """Replay notifications must not cache transient expressions."""
    p = grid()
    source = p.k * p.x
    selected = source(p.i[:1], p.j[:1])
    held = ref(selected)
    del selected
    collect()
    CHECK.assertIsNone(held())
    CHECK.assertEqual(len(source._native_dependents), 0)


@pytest.mark.skipif(not NATIVE, reason="requires native replay dependencies")
def test_ancestor_exposure_does_not_recurse_through_descendants():
    """A long chain captures coefficients before its first owner is edited."""
    p = Prg()
    p.i = I(size=1)
    p.x = V(p.i)
    source = 2 * p.x
    expression, expected = source, 2.0
    for _ in range(1200):
        expression = expression * 1.01
        expected *= 1.01
    source[0].A[0] = 17
    CHECK.assertEqual(expression[0].A, [expected])


@pytest.mark.skipif(not NATIVE, reason="requires native row ownership")
def test_native_row_selection_checks_bounds_and_exact_coefficients():
    """
    Exercise native repeated IDs, detached export and checked integer math.
    """
    rows = import_module("gana._native").AffineRows(
        [
            ([(0, 5, 1)], [2**100 + 1], 3),
            ([(0, 9, 4)], [-7], -2),
        ],
    )
    selected = rows.take([1, 0, 1]).take([2, 1])
    CHECK.assertEqual(selected.columns(0), [4])
    CHECK.assertEqual(selected.coefficients(1), [2**100 + 1])
    CHECK.assertEqual(selected.offsets(), [-2, 3])
    CHECK.assertTrue(selected.contains(0, 5))
    CHECK.assertEqual(selected.sum_all().matrix(0), [(4, -7), (1, 2**100 + 1)])
    CHECK.assertEqual(len(rows.take([])), 0)
    with CHECK.assertRaises(IndexError):
        selected.take([2])
    CHECK.assertEqual(rows.offsets(), [3, -2])


@pytest.mark.parametrize("chain", [False, True])
def test_public_expression_selection_uses_last_duplicate_after_arithmetic(
    chain,
):
    """
    A repeated coordinate may acquire different offsets after broadcasting.
    """
    p = Prg()
    p.i = I(size=2)
    p.x = V(p.i)
    repeated = p.i[:]
    repeated._ = [p.i[1], p.i[1], p.i[0]]
    offsets = [10, 20, 30]
    source = (2 * p.x)(repeated)
    if chain:
        source = 3 * source * 2
    expression = source + offsets
    selected = expression(p.i)
    CHECK.assertEqual([row.B for row in selected], [-30, -20])
    CHECK.assertEqual([row.A for row in selected], [[12 if chain else 2]] * 2)
