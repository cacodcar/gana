"""Compact coordinate roots preserve growth, record updates and copies."""

from copy import deepcopy
from importlib import import_module
from itertools import product
from unittest import TestCase

import pytest

from gana.indexing.coordinates import Positions

CHECK = TestCase()


@pytest.mark.parametrize("direct", [False, True])
def test_cartesian_owner_growth_and_exact_records(direct):
    """Both constructors preserve IDs, exact bounds and atomic appends."""
    native = import_module("gana._native")
    axes = [[8, 3], [7, 2]]
    keys = [list(key) for key in product(*axes)]
    bounds = ((str(-(2**150)), 0.0), (str(2**150 + 1), 0.0))
    constructor = (
        native.MemberTable.cartesian if direct else native.MemberTable
    )
    root = constructor(
        axes if direct else keys,
        [10, 11, 12, 13],
        [bounds] * 4,
    )
    fixed = root.freeze()
    view = root.take([3, 0, 3])
    with CHECK.assertRaises(IndexError):
        root.append([[9, 7], [8, 7]], [14, 15], [None, None])
    CHECK.assertEqual(len(root), 4)
    root.append([[9, 7], [9, 2]], [14, 15], [None, None])
    CHECK.assertEqual(len(fixed), 4)
    with CHECK.assertRaises(IndexError):
        fixed.lookup([9, 7])
    selected, _ = root.product([[9, 3], [2, 7]])
    CHECK.assertEqual([selected.number(n) for n in range(4)], [15, 14, 13, 12])
    CHECK.assertEqual(root.lookup_many(keys), list(range(4)))
    CHECK.assertEqual(root.key(5), [9, 2])
    CHECK.assertEqual(view.bounds(0), bounds)
    view.set_bounds(0, (("-9", 0.0), ("11", 0.0)))
    CHECK.assertEqual(fixed.bounds(3), (("-9", 0.0), ("11", 0.0)))


@pytest.mark.parametrize("axes", [[], [[]], [[4], []], [[4, 1], [3, 7, 2]]])
def test_direct_cartesian_cardinality_and_export(axes):
    """Direct construction follows itertools.product, including rank zero."""
    native = import_module("gana._native")
    keys = list(product(*axes))
    root = native.MemberTable.cartesian(
        axes,
        list(range(len(keys))),
        [None] * len(keys),
    )
    CHECK.assertEqual(
        root.export(),
        [(list(key), n, None) for n, key in enumerate(keys)],
    )
    CHECK.assertEqual(
        root.lookup_many([list(key) for key in keys]),
        list(range(len(keys))),
    )


def test_cartesian_positions_copy_preserves_shared_atoms_and_owner():
    """Copying selections retains shared ownership after sparse-tail growth."""
    axes = (("north", "south"), ("summer", "winter"))
    root = Positions.create(list(product(*axes)))
    view = root.take([3, 0, 3])
    root.owner.append([("west", "summer")], [4], [None])
    copied_root, copied_view = deepcopy((root, view))
    CHECK.assertIs(copied_root.owner, copied_view.owner)
    CHECK.assertEqual(
        list(copied_view),
        [
            ("south", "winter"),
            ("north", "summer"),
            ("south", "winter"),
        ],
    )
    CHECK.assertEqual(copied_root[("west", "summer")], 4)
    CHECK.assertEqual(copied_view[("south", "winter")], 0)
    with CHECK.assertRaises(KeyError):
        copied_view[("west", "summer")]


def test_direct_cartesian_rejects_invalid_axes_and_record_lengths():
    """Reject duplicate axes and mismatched records at the native boundary."""
    table = import_module("gana._native").MemberTable
    with CHECK.assertRaises(IndexError):
        table.cartesian([[1, 1]], [0, 1], [None, None])
    with CHECK.assertRaises(ValueError):
        table.cartesian([[1, 2]], [0], [None])
    with CHECK.assertRaises(ValueError):
        table.cartesian([[1]], [0], [])
