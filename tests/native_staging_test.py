"""Compact declarations retain editable staging and Cartesian order."""

from copy import copy, deepcopy
from itertools import product
from unittest import TestCase

import pytest

from gana import I, P, Prg, T, V
from gana.indexing.coordinates import CoordinateOwner
from gana.indexing.staging import CartesianMap
from gana.storage.parameters import NATIVE

CHECK = TestCase()
pytestmark = pytest.mark.skipif(
    not NATIVE,
    reason="native declaration storage",
)


def declaration(kind, *axes):
    """Construct each family with distinguishable ordered payloads."""
    size = len(list(product(*axes)))
    options = {P: {"_": list(range(size))}, V: {}, T: {"_": (-2, 5)}}
    return kind(*axes, **options[kind])


@pytest.mark.parametrize("kind", [P, V, T])
def test_registration_never_expands_untouched_staging(kind, monkeypatch):
    """
    The frontend reaches direct native construction with no row traversal.
    """
    p = Prg()
    p.i, p.j = I(size=3), I(size=2)
    root = declaration(kind, p.i, p.j)
    CHECK.assertIsInstance(root.map, CartesianMap)
    escaped = root.map

    def reject_expansion(self):
        """Fail if registration reads even one expanded staging coordinate."""
        pytest.fail("registration expanded the Cartesian staging map")

    with monkeypatch.context() as patch:
        patch.setattr(CartesianMap, "_dict", reject_expansion)
        p.data = root
    CHECK.assertTrue(escaped.compact)
    CHECK.assertEqual(list(root.map), list(product(p.i, p.j)))
    if kind is P:
        CHECK.assertEqual(list(root._), list(range(6)))
    else:
        CHECK.assertEqual([member.n for member in root], list(range(6)))


@pytest.mark.parametrize("kind", [P, V, T])
def test_axis_snapshot_duplicates_empty_and_sparse_fallback(kind):
    """Snapshot membership at construction; preserve duplicate collapse."""
    p = Prg()
    p.i, p.j = I(size=3), I(size=2)
    repeated = p.i[:]
    repeated._[:] = [p.i[2], p.i[0], p.i[2]]
    options = {P: {"_": [7, 8, 9, 10]}, V: {}, T: {"_": (0, 1)}}
    root = kind(repeated, p.j, **options[kind])
    expected = list(product([p.i[2], p.i[0]], p.j))
    repeated._.reverse()
    p.data = root
    CHECK.assertEqual(list(root.map), expected)
    empty = declaration(kind, p.i[:0], p.j)
    p.empty = empty
    CHECK.assertEqual(list(empty.map), [])
    groups = ((p.i[:1], p.j), (p.i[2:], p.j))
    sparse = kind(*groups, **options[kind])
    CHECK.assertIs(type(sparse.map), dict)
    p.sparse = sparse
    CHECK.assertEqual(
        list(sparse.map),
        list(product(p.i[:1], p.j)) + list(product(p.i[2:], p.j)),
    )


@pytest.mark.parametrize("kind", [P, V, T])
def test_edited_coordinates_use_final_dictionary_order(kind):
    """
    Valid raw coordinate replacement takes the irregular registration path.
    """
    p = Prg()
    p.i = I(size=3)
    root = declaration(kind, p.i)
    key = (p.i[0],)
    value = root.map.pop(key)
    root.map[("replacement",)] = value
    if kind is P:
        root._[:] = [1, 2, 0]
    expected = list(root.map)
    p.data = root
    CHECK.assertEqual(list(root.map), expected)
    CHECK.assertEqual(len(root), 3)


def test_compact_parameter_buffers_are_validated_independently():
    """A list edit cannot silently change the untouched map's staged values."""
    p = Prg()
    p.i = I(size=2)
    root = P(p.i, _=[1, 2])
    root._[-1] = 99
    with pytest.raises(ValueError, match="disagree"):
        p.data = root
    CHECK.assertTrue(root.map.compact)
    CHECK.assertFalse(hasattr(p, "data"))
    root._[-1] = 2
    p.data = root
    CHECK.assertEqual(list(root._), [1, 2])


def test_raw_map_views_edits_and_iteration_match_dict():
    """Escaped views, LIFO popitem and mutation errors retain dict behavior."""
    mapping = CartesianMap([[0, 1], [2, 3]])
    mapping.fill([4, 5, 6, 7])
    expected = dict(zip(product([0, 1], [2, 3]), [4, 5, 6, 7]))
    view = mapping.items()
    CHECK.assertEqual(mapping.popitem(), expected.popitem())
    mapping.update({("new",): 8})
    expected.update({("new",): 8})
    CHECK.assertEqual(list(view), list(expected.items()))
    CHECK.assertEqual(list(reversed(mapping)), list(reversed(expected)))
    CHECK.assertEqual(mapping.copy(), expected)
    shallow = copy(mapping)
    shallow[("detached",)] = 99
    CHECK.assertNotIn(("detached",), mapping)
    CHECK.assertEqual(mapping | {("x",): 9}, expected | {("x",): 9})
    CHECK.assertEqual({("x",): 9} | mapping, {("x",): 9} | expected)
    mapping |= {("y",): 10}
    iterator = iter(mapping)
    next(iterator)
    mapping[("z",)] = 11
    with pytest.raises(RuntimeError, match="changed size"):
        next(iterator)
    with pytest.raises(TypeError):
        mapping[[]] = 0
    mapping.clear()
    CHECK.assertEqual(list(view), [])


def test_deepcopy_keeps_independent_staging_and_shared_axis_identity():
    """
    Copying an unregistered declaration preserves independent raw buffers.
    """
    p = Prg()
    p.i = I(size=2)
    root = P(p.i, _=[1, 2])
    restored = deepcopy(root)
    CHECK.assertTrue(root.map.compact)
    CHECK.assertTrue(restored.map.compact)
    CHECK.assertIs(restored.map.axes[0][0], restored.index[0][0])
    restored._[0] = 7
    CHECK.assertEqual(list(root.map.values()), [1, 2])
    CHECK.assertEqual(list(restored.map.values()), [1, 2])


def test_direct_owner_keeps_first_product_atom_identity():
    """
    Equal atoms on different axes retain the expanded path's representative.
    """
    first, equal = int("1000"), float("1000")
    axes = ((0, first), (equal, 1))
    keys = list(product(*axes))
    numbers, bounds = list(range(4)), [None] * 4
    before = CoordinateOwner(keys, numbers, bounds)
    after = CoordinateOwner.cartesian(axes, numbers, bounds)
    CHECK.assertEqual(before.atoms, after.atoms)
    for old, new in zip(before.atoms, after.atoms):
        CHECK.assertIs(old, new)
    CHECK.assertEqual(before.handle.export(), after.handle.export())
