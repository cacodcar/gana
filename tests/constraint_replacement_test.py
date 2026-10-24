"""Constraint replacement retains aliases, order and compact siblings."""

from copy import deepcopy
from unittest import TestCase

import pytest

from gana import I, Prg, V
from gana.storage.parameters import NATIVE
from gana.storage.symbols import SymbolRegistry

CHECK = TestCase()
UPPER, EQUALITY, REPLACEMENT = 8, 9, 10
GROWTH, EXTRA = 14, 6


def model():
    """Use independent variable owners and all three solver row groups."""
    p = Prg()
    p.i = I(size=4)
    p.x, p.y = V(p.i), V(p.i)
    p.first = 2 * p.x <= UPPER
    p.eq = 3 * p.y == EQUALITY
    p.bound = p.x >= 0
    return p


def matrix(size):
    """Specify replacement coefficients independently of Gana construction."""
    expected = []
    for position in range(size):
        row = [0] * 8
        row[position] = 5
        expected.append(row)
    for position in range(4):
        row = [0] * 8
        row[4 + position] = 3
        expected.append(row)
    for position in range(4):
        row = [0] * 8
        row[position] = -1
        expected.append(row)
    return expected


def expose_rows(p, expose):
    """Request row or membership aliases before replacing their constraint."""
    held = p.first[0] if expose in {"row", "links"} else None
    links = p.x[0].cons_by if expose == "links" else None
    if expose == "old":
        list(p.first._)
    if expose == "other":
        list(p.eq._)
    return held, links


@pytest.mark.parametrize("size", [1, 3])
@pytest.mark.parametrize("expose", ["none", "row", "links", "old", "other"])
def test_replacement_preserves_compact_siblings_and_memberships(size, expose):
    """Changing one batch retains numeric rows, aliases and list updates."""
    p = model()
    old, registry = p.first, p.constraints
    held, links = expose_rows(p, expose)
    p.first.categorize("Capacity")
    p.first = 5 * p.x(p.i[:size]) <= REPLACEMENT
    if NATIVE:
        CHECK.assertIsInstance(p.constraints, SymbolRegistry)
        CHECK.assertIsNot(p.constraints, registry)
        if expose != "other":
            CHECK.assertNotIn("_legacy_cache", p.eq.__dict__)
            CHECK.assertFalse(p.eq.__dict__.get("_native_rows"))
    CHECK.assertEqual(p.n_constraints, size + 8)
    CHECK.assertEqual(p.first.category, "Capacity")
    expected = matrix(size)
    CHECK.assertEqual(p.A, expected)
    CHECK.assertEqual(p.B, [10] * size + [9] * 4 + [0] * 4)
    CHECK.assertEqual(p.cons(n=True), list(range(size + 8)))
    if NATIVE:
        CHECK.assertIs(registry[0], old[0])
    if held is not None:
        CHECK.assertIs(old[0], held)
    if links is not None:
        check_links(p, held, links)


def check_links(p, held, links):
    """Escaped lists retain identity, order and inverse positions."""
    CHECK.assertIs(p.x[0].cons_by, links)
    CHECK.assertFalse(any(row is held for row in links))
    CHECK.assertEqual(
        [id(row) for row in links],
        [id(p.bound[0]), id(p.first[0])],
    )
    for number, row in enumerate(links):
        CHECK.assertEqual(row.cons_by_pos[p.x[0]], number)


def test_successive_replacements_keep_later_additions_compact():
    """Shrinking/growing replacements do not expand a different owner."""
    p = model()
    for size in (2, 4, 1):
        p.first = 7 * p.x(p.i[:size]) <= GROWTH
    p.extra = 2 * p.y <= EXTRA
    if NATIVE:
        CHECK.assertIsInstance(p.constraints, SymbolRegistry)
        for root in (p.eq, p.extra):
            CHECK.assertNotIn("_legacy_cache", root.__dict__)
            CHECK.assertFalse(root.__dict__.get("_native_rows"))
    p.renumber()
    CHECK.assertEqual(p.cons(n=True), list(range(13)))
    CHECK.assertEqual(p.B, [14] + [6] * 4 + [9] * 4 + [0] * 4)


def test_replacement_copy_retains_escaped_row_aliases():
    """A copied program and held row reference the same copied object."""
    p = model()
    held = p.eq[1]
    p.first = 5 * p.x(p.i[:2]) <= REPLACEMENT
    clone, copied = deepcopy((p, held))
    CHECK.assertIs(clone.eq[1], copied)
    CHECK.assertEqual(clone.A, p.A)
    copied.function.A[0] = 11
    CHECK.assertEqual(clone.A[3][5], 11)
    CHECK.assertEqual(p.A[3][5], 3)


def test_renumber_honors_edited_scalar_relations():
    """Equality/nonnegativity edits preserve per-row ordering."""
    p = model()
    p.eq[1].leq = True
    p.eq[2].nn = True
    p.first = 5 * p.x(p.i[:1]) <= REPLACEMENT
    rows = p.cons()
    expected = {id(row): number for number, row in enumerate(rows)}
    CHECK.assertEqual(
        [row.n for row in rows],
        [expected[id(row)] for row in rows],
    )
    CHECK.assertEqual(p.eq[1].n, 1)
    CHECK.assertEqual(p.eq[2].n, 5)


def test_shared_scalar_rows_keep_identity_removal_fallback():
    """Replacing a root removes its aliased row from another legacy set."""
    p = model()
    shared = p.first._[0]
    p.eq._[1] = shared
    if not NATIVE:
        # Python registration already copied the rows into its own list.
        p.constraints[5] = shared
    survivor = p.eq._[0]
    p.first = 5 * p.x(p.i[:1]) <= REPLACEMENT
    CHECK.assertFalse(any(row is shared for row in p.constraints))
    CHECK.assertTrue(any(row is survivor for row in p.constraints))
    CHECK.assertEqual(len(p.constraints), 8)


def test_duplicate_root_registration_retains_existing_replacement_semantics():
    """Repeated registrations remove matching rows once at their first slot."""
    p = model()
    old = p.first
    p.alias = old
    p.first = 5 * p.x(p.i[:1]) <= REPLACEMENT
    CHECK.assertEqual(len(p.constraints), 9)
    CHECK.assertEqual(p.n_constraints, 9)
    CHECK.assertFalse(any(row.parent is old for row in p.constraints))
