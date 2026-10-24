"""Public list-iteration semantics across lazy selection and local edits."""

from itertools import islice
from unittest import TestCase

import pytest

from gana import I, P, Prg, T, V
from gana.indexing.coordinates import Positions
from gana.storage.parameters import NATIVE

CHECK = TestCase()


def selected_values(kind):
    """Build six list slots with gaps followed by four identifiable values."""
    p = Prg()
    p.i, p.j = I(size=2), I(size=2)
    args = {P: {"_": [0, 1, 2, 3]}, V: {}, T: {"_": (-2, 7)}}[kind]
    p.e = kind(p.i, p.j, **args)
    return p, p.e([None, *p.i], p.j)


def numbers(values, kind):
    """Read numbers or column IDs without invoking symbolic equality."""
    return [item if item is None or kind is P else item.n for item in values]


def edit(values, operation):
    """Apply the same public list edit to the view and an ordinary list."""
    if operation == "replace":
        values[1:3] = [None, None, None]
    elif operation == "insert":
        values.insert(0, None)
    elif operation == "delete":
        del values[0]
    elif operation == "extend":
        values.extend([None, None])
    else:
        values.clear()


@pytest.mark.parametrize("kind", [P, V, T])
@pytest.mark.parametrize("prefix", [0, 1, 6])
@pytest.mark.parametrize(
    "operation",
    ["replace", "insert", "delete", "extend", "clear"],
)
def test_iteration_observes_local_edits(kind, prefix, operation):
    """Mid-iteration edits follow an ordinary list's ordinal cursor exactly."""
    _, selected = selected_values(kind)
    reference = [None, None, 0, 1, 2, 3]
    actual, expected = iter(selected._), iter(reference)
    CHECK.assertEqual(
        numbers(islice(actual, prefix), kind),
        list(islice(expected, prefix)),
    )
    edit(selected._, operation)
    edit(reference, operation)
    CHECK.assertEqual(numbers(actual, kind), list(expected))


@pytest.mark.parametrize("kind", [P, V, T])
def test_exhausted_iterator_stays_exhausted(kind):
    """Appending after StopIteration must not restart a completed iterator."""
    _, selected = selected_values(kind)
    iterator = iter(selected._)
    CHECK.assertEqual(numbers(iterator, kind), [None, None, 0, 1, 2, 3])
    selected._.append(None)
    CHECK.assertEqual(list(iterator), [])
    CHECK.assertEqual(
        numbers(selected._, kind),
        [None, None, 0, 1, 2, 3, None],
    )


@pytest.mark.skipif(not NATIVE, reason="native lazy member ownership")
@pytest.mark.parametrize("kind", [V, T])
def test_partial_iteration_only_creates_consumed_symbols(kind):
    """Iteration allocates only the symbolic members it has consumed."""
    p, selected = selected_values(kind)
    iterator = iter(selected._)
    CHECK.assertEqual(p.e._symbol_storage.states, {})
    CHECK.assertEqual(list(islice(iterator, 2)), [None, None])
    CHECK.assertEqual(p.e._symbol_storage.states, {})
    CHECK.assertEqual(next(iterator).n, 0)
    CHECK.assertEqual(set(p.e._symbol_storage.states), {0})


@pytest.mark.skipif(not NATIVE, reason="native coordinate interning")
def test_equal_atoms_share_stable_tokens_through_growth():
    """Equal Python keys reuse the original atom, including token zero."""
    positions = Positions.create([(1, "a"), (True, "b"), (0, "a")])
    atoms = positions.owner.atoms
    CHECK.assertEqual(atoms, [1, "a", "b", 0])
    CHECK.assertIs(type(atoms[0]), int)
    CHECK.assertEqual(positions[(True, "a")], 0)
    frozen = positions.freeze()
    positions.owner.append([(False, "b")], [3], [None])
    CHECK.assertEqual(positions.owner.atoms, atoms)
    CHECK.assertEqual(positions[(0, "b")], 3)
    with pytest.raises(KeyError):
        frozen[(0, "b")]
    with pytest.raises(IndexError):
        positions.owner.append([(True, "a")], [4], [None])
    CHECK.assertEqual(
        list(positions),
        [(1, "a"), (1, "b"), (0, "a"), (0, "b")],
    )
