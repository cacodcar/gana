"""Local membership edits must survive registration, replay and graph
copying.
"""

import pickle
from copy import deepcopy
from unittest import TestCase

import pytest

from gana import I, Prg, V
from gana.backends.native.constraints import compile_program
from gana.storage.parameters import NATIVE

from .native_membership_test import clone_fixture

CHECK = TestCase()
pytestmark = pytest.mark.skipif(
    not NATIVE,
    reason="requires native membership",
)


def model():
    """Use overlapping owners so accidental predecessor replay is visible."""
    p = Prg()
    p.i = I(size=6)
    p.x, p.y = V(p.i), V(p.i)
    bound = 20
    p.first = 2 * p.y <= bound
    p.middle = p.x + p.y <= bound
    p.last = 3 * p.x <= bound
    return p


def edit(values, mutation):
    """Exercise public list operations without replacing the escaped list."""
    operations = {
        "clear": values.clear,
        "reverse": values.reverse,
        "pop": values.pop,
        "remove": lambda: values.remove(values[0]),
        "append": lambda: values.append(values[0]),
        "extend": lambda: values.extend(values[:]),
        "insert": lambda: values.insert(1, values[0]),
        "set": lambda: values.__setitem__(slice(None), values[::-1]),
        "delete": lambda: values.__delitem__(slice(0, 1)),
        "iadd": lambda: values.__iadd__(values[:1]),
        "imul": lambda: values.__imul__(2),
        "sort": lambda: values.sort(key=lambda row: row.parent.pname),
    }
    return operations[mutation]()


def register(p):
    """Append a newly registered occurrence to already exposed lists."""
    bound = 15
    p.extra = 4 * p.x <= bound


def replay(p):
    """Replay overlapping predecessors after the list has been edited."""
    p.last._materialize()


def structural_edit(p):
    """A coefficient edit must still promote and preserve scalar identity."""
    p.middle[3].A[0] = 7


def replace(p):
    """Replacing a registered constraint must detach its old occurrences."""
    bound = 17
    p.middle = 5 * p.x <= bound


def memberships(p):
    """Compare logical links, inverse maps and row aliases with ordinary
    rows.
    """
    result = []
    for variable in (p.x[3], p.y[3], p.x[5], p.y[5]):
        values = variable.cons_by
        result.append([(row.parent.pname, row.pos) for row in values])
        for row in values:
            CHECK.assertIs(row, getattr(p, row.parent.pname)[row.pos])
    for source in p.constraint_sets:
        for position in (3, 5):
            row = source[position]
            result.append(
                sorted(
                    (variable.n, n) for variable, n in row.cons_by_pos.items()
                ),
            )
    return result


@pytest.mark.parametrize(
    "mutation",
    [
        "clear",
        "reverse",
        "pop",
        "remove",
        "append",
        "extend",
        "insert",
        "set",
        "delete",
        "iadd",
        "imul",
        "sort",
    ],
)
@pytest.mark.parametrize(
    "followup",
    [register, replay, structural_edit, replace],
)
def test_local_edit_survives_later_bookkeeping(mutation, followup):
    """All list mutators retain legacy behavior across subsequent graph
    changes.
    """
    p, reference = model(), model()
    replay(reference)
    values = p.x[3].cons_by
    held_row = p.last[3]
    edit(values, mutation)
    edit(reference.x[3].cons_by, mutation)
    CHECK.assertIs(p.x[3].cons_by, values)
    CHECK.assertIsNotNone(compile_program(p))
    CHECK.assertNotIn("_native_rows", p.first.__dict__)
    for source in (p.middle, p.last):
        CHECK.assertEqual(set(source._native_rows), {3})
        CHECK.assertNotIn("_legacy_cache", source.__dict__)
    followup(p)
    followup(reference)
    CHECK.assertIs(p.x[3].cons_by, values)
    CHECK.assertIs(p.last[3], held_row)
    CHECK.assertEqual(memberships(p), memberships(reference))
    CHECK.assertEqual(p.A, reference.A)
    CHECK.assertEqual(p.B, reference.B)


@pytest.mark.parametrize("method", ["deepcopy", "pickle"])
@pytest.mark.parametrize("mutation", ["clear", "reverse", "extend"])
@pytest.mark.parametrize("target", ["program", "list", "bundle"])
def test_edited_membership_copy_preserves_graph_aliases(
    method,
    mutation,
    target,
):
    """Copying a list alone or beside its owner retains one authoritative
    graph.
    """
    p = model()
    values = p.x[3].cons_by
    edit(values, mutation)
    expected = [(row.parent.pname, row.pos) for row in values]
    inputs = {"program": p, "list": values, "bundle": (values, p)}
    copied = clone_fixture(
        inputs[target],
        deepcopy if method == "deepcopy" else pickle,
    )
    if target == "program":
        result = copied.x[3].cons_by
    elif target == "bundle":
        result, owner = copied
        CHECK.assertIs(result, owner.x[3].cons_by)
    else:
        result = copied
    CHECK.assertEqual(
        [(row.parent.pname, row.pos) for row in result],
        expected,
    )
    CHECK.assertIsNot(result, values)
    CHECK.assertIs(p.x[3].cons_by, values)
    for row in result:
        CHECK.assertIs(row, row.parent[row.pos])


def test_empty_membership_edit_stays_lazy_and_observes_registration():
    """Editing an empty resolved list must not create unrelated coordinates."""
    p = Prg()
    p.i = I(size=6)
    p.x = V(p.i)
    bound = 9
    p.selected = 2 * p.x(p.i[::2]) <= bound
    values = p.x[3].cons_by
    values.clear()
    CHECK.assertEqual(values, [])
    CHECK.assertNotIn("_native_rows", p.selected.__dict__)
    register(p)
    CHECK.assertIs(p.x[3].cons_by, values)
    CHECK.assertEqual(list(map(id, values)), [id(p.extra[3])])
    CHECK.assertIsNotNone(compile_program(p))
