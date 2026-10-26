"""Resolved inverse membership edits preserve aliases and later bookkeeping."""

import pickle
from copy import deepcopy
from unittest import TestCase

import pytest

from gana.backends.native.constraints import compile_program

from .native_membership_edit_test import (
    memberships,
    model,
    register,
    replace,
    replay,
    structural_edit,
)
from .native_membership_test import clone_fixture

CHECK = TestCase()


def edit(values, mutation, variable):
    """Exercise ordinary dict mutators through an escaped inverse mapping."""
    operations = {
        "clear": values.clear,
        "set": lambda: values.__setitem__(variable, 41),
        "delete": lambda: values.__delitem__(variable),
        "pop": lambda: values.pop(variable),
        "popitem": values.popitem,
        "update": lambda: values.update({variable: 41}),
        "setdefault": lambda: values.setdefault(variable, 41),
        "ior": lambda: values.__ior__({variable: 41}),
    }
    return operations[mutation]()


@pytest.mark.parametrize(
    "mutation",
    [
        "clear",
        "set",
        "delete",
        "pop",
        "popitem",
        "update",
        "setdefault",
        "ior",
    ],
)
@pytest.mark.parametrize(
    "followup",
    [register, replay, structural_edit, replace],
)
def test_position_edit_stays_local_and_survives_followup(mutation, followup):
    """Match ordinary inverse-map edits through registration and replay."""
    p, reference = model(), model()
    replay(reference)
    row = p.middle[3]
    positions = row.cons_by_pos
    keys = positions.keys()
    edit(positions, mutation, p.x[3])
    edit(reference.middle[3].cons_by_pos, mutation, reference.x[3])
    CHECK.assertIs(row.cons_by_pos, positions)
    CHECK.assertIsNotNone(compile_program(p))
    for source in p.constraint_sets:
        CHECK.assertEqual(set(source._native_rows), {3})
        CHECK.assertNotIn("_legacy_cache", source.__dict__)
    followup(p)
    followup(reference)
    CHECK.assertIs(row.cons_by_pos, positions)
    CHECK.assertEqual(list(keys), list(positions))
    CHECK.assertEqual(memberships(p), memberships(reference))
    CHECK.assertEqual(p.A, reference.A)
    CHECK.assertEqual(p.B, reference.B)


@pytest.mark.parametrize("method", ["deepcopy", "pickle"])
@pytest.mark.parametrize("mutation", ["clear", "set", "delete"])
@pytest.mark.parametrize("target", ["program", "mapping", "bundle"])
def test_position_copy_memoizes_one_graph(method, mutation, target):
    """Copy a mapping alone or with its owner without duplicate aliases."""
    p = model()
    values = p.middle[3].cons_by_pos
    edit(values, mutation, p.x[3])
    expected = [
        (variable.n, position) for variable, position in values.items()
    ]
    inputs = {"program": p, "mapping": values, "bundle": (values, p)}
    copied = clone_fixture(
        inputs[target],
        deepcopy if method == "deepcopy" else pickle,
    )
    if target == "program":
        result = copied.middle[3].cons_by_pos
    elif target == "bundle":
        result, owner = copied
        CHECK.assertIs(result, owner.middle[3].cons_by_pos)
    else:
        result = copied
    CHECK.assertEqual(
        [(variable.n, position) for variable, position in result.items()],
        expected,
    )
    CHECK.assertIsNot(result, values)
    CHECK.assertIs(p.middle[3].cons_by_pos, values)
    for variable in result:
        middle = next(
            row for row in variable.cons_by if row.parent.pname == "middle"
        )
        CHECK.assertIs(middle.cons_by_pos, result)


def test_added_mapping_key_survives_replay_and_structural_edit():
    """Caller-added bookkeeping entries remain authoritative until detached."""
    p, reference = model(), model()
    replay(reference)
    values = p.middle[3].cons_by_pos
    values[p.x[5]] = 71
    reference.middle[3].cons_by_pos[reference.x[5]] = 71
    structural_edit(p)
    structural_edit(reference)
    CHECK.assertIs(p.middle[3].cons_by_pos, values)
    CHECK.assertEqual(memberships(p), memberships(reference))


@pytest.mark.parametrize("kind", ["expression", "constraint"])
def test_cached_index_conversion_can_promote_the_owner(kind):
    """Index conversion may mutate rows before the cached read returns."""
    p = model()
    source = p.middle.function if kind == "expression" else p.middle
    row = source[0]
    coefficients = row.A

    class Index:
        """Apply a public edit while resolving a Python integer index."""

        def __index__(self):
            """Replay before returning the exposed coordinate."""
            coefficients[0] = 9
            return 0

    CHECK.assertIs(source[Index()], row)
    CHECK.assertIs(row.A, coefficients)
    CHECK.assertEqual(row.A[0], 9)
    CHECK.assertIs(source[-len(source)], row)
    with pytest.raises(IndexError):
        _ = source[len(source)]


def test_protected_container_reads_keep_snapshot_mutation_guards():
    """Repeated reads cannot bypass the first-write snapshot transaction."""
    p = model()
    source = p.middle.function
    derived = 2 * source
    row = source[0]
    coefficients = row.A
    for _ in range(4):
        CHECK.assertIs(source[0], row)
        CHECK.assertIs(row.A, coefficients)
    coefficients[0] = 7
    CHECK.assertEqual(source[0].A, [7, 1])
    CHECK.assertEqual(derived[0].A, [2, 2])
