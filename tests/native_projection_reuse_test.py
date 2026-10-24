"""Repeated projection must retain row identity and release temporary plans."""

import gc
from copy import deepcopy
from unittest import TestCase
from weakref import ref

import pytest

from gana import I, Prg, V
from gana.backends.native import rows as native_rows
from gana.backends.native.algebra import _DISPLAY
from gana.storage.parameters import NATIVE

CHECK = TestCase()
pytestmark = pytest.mark.skipif(not NATIVE, reason="requires native rows")


def model():
    """Build shared nested operands and overlapping constraint memberships."""
    p = Prg()
    p.i = I(size=6)
    p.x, p.y = V(p.i), V(p.i)
    p.f = 2 * p.x + p.y
    bound = 20
    p.c = p.f <= bound
    return p


@pytest.mark.parametrize("kind", ["expression", "constraint", "membership"])
def test_repeated_projection_keeps_partial_rows_and_context(kind):
    """Reuse partial work while leaving siblings lazy and context isolated."""
    p = model()
    source = p.f if kind == "expression" else p.c.function
    access = {
        "expression": lambda n: p.f[n],
        "constraint": lambda n: p.c[n],
        "membership": lambda n: p.x[n].cons_by[0],
    }[kind]
    first = access(0)
    CHECK.assertNotIn("_native_row_renderer", source.__dict__)
    access(1)
    plan = source._native_row_renderer
    access(2)
    CHECK.assertIs(source._native_row_renderer, plan)
    CHECK.assertIs(access(0), first)
    CHECK.assertEqual(set(source._native_rows), {0, 1, 2})
    CHECK.assertIsNone(_DISPLAY.get())
    for position in range(3, len(p.i)):
        row = access(position)
        CHECK.assertEqual(row.A, [2, 1])
    CHECK.assertNotIn("_native_row_renderer", source.__dict__)
    CHECK.assertNotIn("_legacy_cache", source.__dict__)


@pytest.mark.parametrize("kind", ["expression", "constraint", "membership"])
def test_mutation_releases_plan_and_preserves_exposed_rows(kind):
    """Structural edits replay; resolved membership edits retain projection."""
    p = model()
    rows = [p.c[n] for n in range(3)]
    links = p.x[0].cons_by
    if kind == "membership":
        links.reverse()
    elif kind == "constraint":
        rows[0].leq = False
    else:
        rows[0].A[0] = 7
    if kind == "membership":
        CHECK.assertIn("_native_row_renderer", p.c.function.__dict__)
        CHECK.assertNotIn("_legacy_cache", p.c.__dict__)
    else:
        CHECK.assertNotIn("_native_row_renderer", p.c.function.__dict__)
    CHECK.assertIs(p.c[0], rows[0])
    CHECK.assertIs(p.x[0].cons_by, links)
    CHECK.assertEqual(p.c[5].A, [2, 1])


def test_partial_plan_copy_preserves_one_copied_graph():
    """Deepcopy completes aliases and omits temporary renderer machinery."""
    p = model()
    for n in range(3):
        _ = p.x[n].cons_by
    q = deepcopy(p)
    CHECK.assertNotIn("_native_row_renderer", p.c.function.__dict__)
    CHECK.assertNotIn("_native_row_renderer", q.c.function.__dict__)
    CHECK.assertIs(q.x[0].cons_by[0], q.c[0])
    CHECK.assertIsNot(q.c[0], p.c[0])
    CHECK.assertEqual(q.A, p.A)


def test_abandoned_partial_plan_is_collectible():
    """A temporary plan must not root the program after all callers drop it."""
    p = model()
    _ = p.c[0]
    _ = p.c[1]
    plan = ref(p.c.function._native_row_renderer)
    owner = ref(p.c.function)
    del p, _
    gc.collect()
    CHECK.assertIsNone(plan())
    CHECK.assertIsNone(owner())


def test_repeated_selected_rows_share_parent_projection():
    """A compact selected view reuses its parent's public rows and plan."""
    p = model()
    selected = p.f(p.i[::2])
    CHECK.assertEqual([row.A for row in selected], [[2, 1]] * 3)
    CHECK.assertIs(p.f[2], selected[1])
    CHECK.assertNotIn("_legacy_cache", p.f.__dict__)


def test_consuming_parent_releases_partial_operand_plan():
    """Nested traversal finishes operand caches without retaining old plans."""
    p = model()
    _ = p.f[0]
    _ = p.f[1]
    CHECK.assertIn("_native_row_renderer", p.f.__dict__)
    rows = list(p.c)
    CHECK.assertEqual(len(rows), len(p.i))
    CHECK.assertNotIn("_native_row_renderer", p.f.__dict__)


def test_failed_row_read_restores_context_and_keeps_existing_rows(monkeypatch):
    """A failed projection cannot poison a subsequent read or its context."""
    p = model()
    first = p.c[0]
    _ = p.c[1]
    original = native_rows._Rows.row
    failure_position = 2

    def fail(self, position):
        """Fail one requested position after its normalization was prepared."""
        if position == failure_position:
            message = "projection fixture failure"
            raise RuntimeError(message)
        return original(self, position)

    monkeypatch.setattr(native_rows._Rows, "row", fail)
    with pytest.raises(RuntimeError, match="projection fixture failure"):
        _ = p.c[2]
    CHECK.assertIsNone(_DISPLAY.get())
    CHECK.assertIs(p.c[0], first)
    CHECK.assertEqual(p.c[3].A, [2, 1])
