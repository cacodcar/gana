"""Lazy indices preserve identity, metadata and coordinate snapshots."""

import gc
import weakref
from copy import copy, deepcopy
from unittest import TestCase

import pytest

from gana import I, P, Prg, T, V
from gana.indexing.ordered import OrderedMembers
from gana.storage.parameters import NATIVE

CHECK = TestCase()
pytestmark = pytest.mark.skipif(not NATIVE, reason="native ordered indices")


@pytest.mark.parametrize("kind", [P, V, T])
def test_native_construction_creates_no_ordered_members(kind):
    """Real owner construction must not defer birth to registration."""
    p = Prg()
    axis = I(size=1000)
    buffer = axis._
    p.i = axis
    p.j = I(size=2)
    family, other = p.i._.family, p.j._.family
    CHECK.assertIs(p.i._, buffer)
    options = {P: {"_": 3}, V: {}, T: {"_": (-2, 5)}}
    p.data = kind(p.i, p.j, **options[kind])
    CHECK.assertEqual(len(p.data), 2000)
    CHECK.assertEqual((family.cache, other.cache), ({}, {}))
    key = next(iter(p.data.map))
    CHECK.assertIs(key[0], p.i[0])
    CHECK.assertIs(key[1], p.j[0])
    CHECK.assertEqual(list(family.cache), [0])
    CHECK.assertEqual(list(other.cache), [0])


def test_partial_reads_keep_frozen_names_metadata_and_identity():
    """A root rename cannot change unborn member names or escaped metadata."""
    p = Prg()
    p.i = I(size=100, start=-3)
    family = p.i._.family
    p.i.name, p.i.start = "renamed", 500
    first, last = p.i[0], p.i[-1]
    CHECK.assertEqual((first.name, last.name), ("i[-3]", "i[96]"))
    first.parameters.append("local")
    first.extra = {"state": [7]}
    CHECK.assertIs(p.i[0], first)
    CHECK.assertEqual(p.i[0].extra, {"state": [7]})
    CHECK.assertEqual(last.parameters, [])
    CHECK.assertIs(p.i[1:3][0], p.i[1])
    CHECK.assertEqual(set(family.cache), {0, 1, 2, 99})
    CHECK.assertIs(type(first), I)
    CHECK.assertIs(first.parent[0], p.i)


def test_same_axis_in_multiple_dimensions_shares_tokens():
    """Repeated axes share identities and native tokens."""
    p = Prg()
    p.i = I(size=4)
    p.x = V(p.i, p.i)
    family = p.i._.family
    CHECK.assertEqual(family.cache, {})
    positions = p.x._symbol_storage.positions
    CHECK.assertEqual(len(positions.owner.atoms), 4)
    CHECK.assertEqual(positions[(p.i[2], p.i[3])], 11)
    CHECK.assertIs(positions.key(10)[0], positions.key(10)[1])
    CHECK.assertEqual(set(family.cache), {2, 3})
    with pytest.raises(KeyError):
        positions[(I(), p.i[0])]


@pytest.mark.parametrize("registered", [False, True])
def test_index_list_edits_cannot_change_captured_coordinates(registered):
    """Staged and registered owners retain membership after raw index edits."""
    p = Prg()
    p.i = I(size=3)
    root = P(p.i, _=[1, 2, 3])
    old_first = p.i[0]
    if registered:
        p.data = root
    p.i._.reverse()
    p.i._.pop()
    p.i._.append(I())
    if not registered:
        p.data = root
    CHECK.assertIs(next(iter(root.map))[0], old_first)
    CHECK.assertEqual(list(root._), [1, 2, 3])
    CHECK.assertIsNot(p.i[0], old_first)


def test_copy_preserves_aliases_and_independent_mutable_metadata():
    """Copied coordinate owners and indices agree on the same copied atoms."""
    p = Prg()
    p.i = I(size=4)
    p.x = V(p.i)
    observed = p.i[2]
    observed.extra = [7]
    restored = deepcopy(p)
    CHECK.assertIsNot(restored.i[2], observed)
    CHECK.assertIs(
        restored.x._symbol_storage.positions.key(2)[0],
        restored.i[2],
    )
    CHECK.assertIs(restored.i[2].parent[0], restored.i)
    restored.i[2].extra.append(8)
    CHECK.assertEqual(observed.extra, [7])
    CHECK.assertIs(restored.x(restored.i[2])[0], restored.x[2])


def test_raw_list_operators_and_mutating_iteration_match_lists():
    """Raw lists retain edits, copying and iterator visibility."""
    p = Prg()
    p.i = I(size=3)
    values = p.i._
    expected = list(p.i)
    CHECK.assertEqual(copy(values), expected)
    empty = []
    CHECK.assertEqual(values + empty, expected)
    CHECK.assertEqual(empty + values, expected)
    CHECK.assertEqual(values * 2, expected * 2)
    CHECK.assertEqual(2 * values, expected * 2)
    iterator = iter(values)
    CHECK.assertIs(next(iterator), expected[0])
    extra = I()
    values.append(extra)
    CHECK.assertEqual(list(iterator), [*expected[1:], extra])
    values[:] = expected
    values *= 2
    values.sort(key=lambda item: item.name, reverse=True)
    CHECK.assertEqual(
        list(values),
        sorted(expected * 2, key=lambda x: x.name, reverse=True),
    )
    with pytest.raises(ValueError):
        values[::2] = []


def test_deleted_members_and_entire_families_can_be_collected():
    """Weak provenance must not cause one retained member to pin siblings."""
    p = Prg()
    p.i = I(size=3)
    first, second = p.i[0], p.i[1]
    reference = weakref.ref(second)
    p.i._.clear()
    del second
    gc.collect()
    CHECK.assertIsNone(reference())
    CHECK.assertIs(first.parent[0], p.i)
    owner = weakref.ref(p.i)
    del first, p
    gc.collect()
    CHECK.assertIsNone(owner())


def test_repeated_birth_and_explicit_buffer_replacement_keep_legacy_behavior():
    """Repeated birth appends; explicit lists retain their identity."""
    root = I(size=2, dummy=True)
    original = list(root)
    root.birth_elements()
    CHECK.assertEqual(len(root), 4)
    CHECK.assertIs(root[0], original[0])
    CHECK.assertIsNot(root[2], original[0])
    replacement = []
    declared = I(size=2)
    declared._ = replacement
    p = Prg()
    p.i = declared
    CHECK.assertIs(p.i._, replacement)
    CHECK.assertEqual(len(replacement), 2)
    CHECK.assertIsInstance(root._, OrderedMembers)


def test_partial_iteration_does_not_create_unread_members():
    """Starting an iterator must keep unobserved indices absent."""
    p = Prg()
    p.i = I(size=100)
    family = p.i._.family
    iterator = iter(p.i)
    CHECK.assertEqual(family.cache, {})
    CHECK.assertIs(next(iterator), p.i[0])
    CHECK.assertEqual(set(family.cache), {0})
    CHECK.assertIs(next(iterator), p.i[1])
    CHECK.assertEqual(set(family.cache), {0, 1})


@pytest.mark.parametrize(
    "edit",
    ["append", "insert", "delete", "clear", "reverse", "replace"],
)
def test_iteration_observes_structural_edits_like_a_list(edit):
    """Suspended iterators see promotion and later positional edits."""
    p = Prg()
    p.i = I(size=4)
    values = p.i._
    expected = list(p.i)
    actual_iterator, expected_iterator = iter(values), iter(expected)
    CHECK.assertIs(next(actual_iterator), next(expected_iterator))
    extra = I()
    for target in (values, expected):
        _edit_members(target, edit, extra)
    CHECK.assertEqual(list(actual_iterator), list(expected_iterator))


def _edit_members(target, edit, extra):
    """Apply the same public sequence edit to the native facade and a list."""
    if edit == "append":
        target.append(extra)
    elif edit == "insert":
        target.insert(0, extra)
    elif edit == "delete":
        del target[0]
    elif edit == "clear":
        target.clear()
    elif edit == "reverse":
        target.reverse()
    else:
        target[:] = [extra, target[-1], target[0]]


def test_iterator_sees_birth_and_rebirth_but_never_revives_after_exhaustion():
    """Membership changes stay visible; exhaustion is permanent."""
    root = I(size=3)
    iterator = iter(root)
    p = Prg()
    p.i = root
    CHECK.assertIs(next(iterator), root[0])
    root._.clear()
    root.birth_elements()
    CHECK.assertEqual(list(iterator), [root[1], root[2]])
    root._.append(I())
    CHECK.assertEqual(list(iterator), [])


def test_iterator_sees_append_after_last_yield_before_exhaustion():
    """Yielding the last element does not exhaust a list iterator yet."""
    p = Prg()
    p.i = I(size=1)
    iterator = iter(p.i)
    CHECK.assertIs(next(iterator), p.i[0])
    extra = I()
    p.i._.append(extra)
    CHECK.assertIs(next(iterator), extra)
    CHECK.assertEqual(list(iterator), [])


def test_suspended_iterator_does_not_pin_removed_siblings():
    """Keep only the yielded member alive after its mutable list is cleared."""
    p = Prg()
    p.i = I(size=3)
    iterator = iter(p.i)
    first = next(iterator)
    sibling = weakref.ref(p.i[1])
    p.i._.clear()
    gc.collect()
    CHECK.assertIsNone(sibling())
    CHECK.assertIs(first.parent[0], p.i)
    CHECK.assertEqual(list(iterator), [])
