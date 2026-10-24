"""Ordered index metadata and shared coordinate interning contracts."""

from copy import deepcopy
from unittest import TestCase

import pytest

from gana import I, P, Prg, T, V
from gana.indexing.coordinates import Positions
from gana.storage.parameters import NATIVE

CHECK = TestCase()


@pytest.mark.parametrize("start", [-3, 0, 7])
@pytest.mark.parametrize("dummy", [False, True])
def test_ordered_members_keep_default_metadata_and_independent_lists(
    start,
    dummy,
):
    """Parent options and local edits never leak into other members."""
    root = I(size=3, start=start, mutable=True, tag="parent", dummy=dummy)
    if not dummy:
        p = Prg()
        p.axis = root
    CHECK.assertEqual(len(root), 3)
    for n, member in enumerate(root):
        CHECK.assertIs(type(member), I)
        CHECK.assertEqual(member.name, f"{root.name}[{start + n}]")
        CHECK.assertEqual(hash(member), hash(member.name))
        CHECK.assertIs(member.parent[0], root)
        CHECK.assertEqual(member.pos, [n])
        CHECK.assertIs(member._[0], member)
        CHECK.assertEqual(member.members, [member.name])
        CHECK.assertEqual((member.size, member.start), (1, 0))
        CHECK.assertTrue(member.ordered)
        CHECK.assertFalse(member.mutable)
        CHECK.assertIsNone(member.tag)
        CHECK.assertIsNone(member.n)
        CHECK.assertIsNone(member.case)
        CHECK.assertIsNone(member.slice)
        CHECK.assertIsNone(member._ltx)
    first, second = root[0], root[1]
    for name in ("parameters", "variables", "functions", "constraints"):
        getattr(first, name).append("local")
        CHECK.assertEqual(getattr(second, name), [])
        CHECK.assertEqual(getattr(root, name), [])
    first.pos.append(99)
    CHECK.assertEqual(second.pos, [1])
    CHECK.assertIs(root[::-1][2], first)
    restored = deepcopy(root)
    CHECK.assertIs(restored[0].parent[0], restored)
    CHECK.assertIs(restored[0]._[0], restored[0])


@pytest.mark.parametrize("kind", [P, V, T])
def test_multiaxis_elements_reuse_ordered_index_identities(kind):
    """P/V/T retain Cartesian order and the same shared Python axis members."""
    p = Prg()
    p.i, p.j = I(size=3, start=4), I(size=2, start=-1)
    values = {P: {"_": [1, 2, 3, 4, 5, 6]}, V: {}, T: {"_": (0, 3)}}
    p.e = kind(p.i, p.j, **values[kind])
    expected = [(i, j) for i in p.i for j in p.j]
    CHECK.assertEqual(len(p.e), 6)
    for actual, original in zip(p.e.map, expected):
        CHECK.assertIs(actual[0], original[0])
        CHECK.assertIs(actual[1], original[1])
    selected = p.e(p.i[::-1], p.j[::2])
    CHECK.assertEqual(
        list(selected.map),
        expected[4:5] + expected[2:3] + expected[:1],
    )
    if kind is P:
        CHECK.assertEqual(list(selected._), [5, 3, 1])
    else:
        CHECK.assertEqual([member.n for member in selected], [4, 2, 0])


class CollidingAtom:
    """Distinct keys with deliberate hash collisions and value equality."""

    def __init__(self, value):
        """Keep identity separate from the equality label."""
        self.value = value

    def __hash__(self):
        """Exercise equality resolution inside one dictionary hash bucket."""
        return 7

    def __eq__(self, other):
        """Equal keys share the first atom's token without replacing it."""
        return isinstance(other, CollidingAtom) and self.value == other.value


@pytest.mark.skipif(not NATIVE, reason="requires native coordinate storage")
def test_equal_colliding_atoms_keep_first_identity_through_growth():
    """Interning and append preserve IDs and fixed snapshot domains."""
    first, equal, other = map(CollidingAtom, ["a", "a", "b"])
    positions = Positions.create(
        [(first, first), (equal, other), (other, first)],
    )
    CHECK.assertEqual(positions[(equal, other)], 1)
    CHECK.assertIs(positions.key(1)[0], first)
    CHECK.assertIs(positions.key(1)[1], other)
    frozen = positions.freeze()
    added = CollidingAtom("c")
    with pytest.raises(ValueError):
        positions.owner.append([(added, first)], [], [None])
    CHECK.assertEqual(len(positions), 3)
    CHECK.assertNotIn(added, positions.owner.tokens)
    positions.owner.append([(added, equal)], [3], [None])
    CHECK.assertEqual(len(positions), 4)
    CHECK.assertEqual(len(frozen), 3)
    CHECK.assertEqual(positions[(added, first)], 3)
    CHECK.assertIs(positions.key(3)[1], first)


@pytest.mark.skipif(not NATIVE, reason="requires native coordinate storage")
def test_empty_coordinates_and_equal_zero_atoms_preserve_root_uniqueness():
    """Equal atoms share tokens, including zero, within unique root rows."""
    positions = Positions.create([(0, 0), (False, None), (None, 0)])
    CHECK.assertEqual(len(positions), 3)
    CHECK.assertEqual(list(positions), [(0, 0), (0, None), (None, 0)])
    CHECK.assertIs(type(positions.key(1)[0]), int)
    CHECK.assertEqual(positions.owner.atoms, [0, None])
    CHECK.assertEqual(list(Positions.create([()])), [()])
    CHECK.assertEqual(list(Positions.create([])), [])
    with pytest.raises(IndexError):
        Positions.create([(0,), (False,)])
