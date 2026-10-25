"""
Coordinate sharing, duplicate lookup and exact compensated offset oracles.
"""

from importlib import import_module
from math import copysign, isnan
from unittest import TestCase

import pytest

from gana import I, Prg, V, sigma
from gana.backends.native.algebra import NativeRows
from gana.indexing.coordinates import Positions

CHECK = TestCase()


@pytest.mark.parametrize("reduced", [False, True])
def test_nested_coordinates_do_not_decode_owner_rows(monkeypatch, reduced):
    """
    Repeated selections share native coordinates, including derived domains.
    """
    p = Prg()
    p.i, p.j = I(size=4), I(size=3)
    p.x = V(p.i, p.j)
    expression = 2 * p.x
    axes = (p.i, p.j)
    if reduced:
        expression = sigma(expression, p.j)
        axes = (p.i,)

    def unexpected_decode(*args):
        """Fail if native slicing expands its coordinate table into Python."""
        pytest.fail("selection decoded an owner coordinate")

    with monkeypatch.context() as patch:
        patch.setattr(Positions, "key", unexpected_decode)
        selected = expression(*(axis[::-1] for axis in axes))
        nested = selected(*(axis[::2] for axis in axes))
    CHECK.assertIsInstance(nested, NativeRows)
    CHECK.assertEqual(p.x._symbol_storage.states, {})
    expected = [[0, 1, 2], [6, 7, 8]] if reduced else [[0], [2], [6], [8]]
    CHECK.assertEqual(
        [nested._native_batch.columns(n) for n in range(len(nested))],
        expected,
    )
    CHECK.assertIs(
        selected._native_domain[1].owner,
        nested._native_domain[1].owner,
    )


@pytest.mark.parametrize("irregular", [False, True])
def test_duplicate_coordinates_choose_last_expression_row(irregular):
    """Different coefficients at repeated keys expose first/last confusion."""
    native = import_module("gana._native")
    keys = [[0, 5], [0, 6], [1, 5], [1, 6]]
    table = native.MemberTable(keys, list(range(4)), [None] * 4)
    if irregular:
        view = table.take([3, 0, 3, 1, 0])
        requested, expected = [[0], [5, 6]], [4, 3]
    else:
        view, _ = table.product([[1, 1, 0], [6, 6]])
        requested, expected = [[1, 0], [6]], [3, 5]
    rows = native.AffineRows.constants(list(range(len(view))))
    _, last = view.product(requested, last=True)
    _, first = view.product(requested)
    CHECK.assertEqual(rows.select(last).offsets(), expected)
    CHECK.assertNotEqual(rows.select(first).offsets(), expected)


@pytest.mark.parametrize(
    "values",
    [
        [1e16, 1.0, -1e16],
        [-0.0, 0.0, -0.0],
        [2**100 + 1, 1.5, -(2**100)],
        [-(2**127), 2**127 - 1, 1],
        [float("inf"), -float("inf"), 1.0],
        [float("nan"), 2.0, -1.0],
    ],
)
@pytest.mark.parametrize("groups", [None, [[2, 0, 1], [], [2, 2]]])
def test_native_offset_reduction_matches_active_interpreter(values, groups):
    """
    Keep compensation, integer boundaries, nonfinite values and zero signs.
    """
    native = import_module("gana._native")
    rows = native.AffineRows(
        [([(0, n, n)], [n + 1], value) for n, value in enumerate(values)],
    )
    reduced = rows.sum_python(groups)
    selected = [list(range(len(values)))] if groups is None else groups
    for n, positions in enumerate(selected):
        expected = -sum(-values[position] or 0 for position in positions)
        actual = reduced.offset(n)
        if isinstance(expected, float) and isnan(expected):
            CHECK.assertTrue(isnan(actual))
        else:
            CHECK.assertEqual(actual, expected)
            CHECK.assertIs(type(actual), type(expected))
            CHECK.assertEqual(copysign(1, actual), copysign(1, expected))
        CHECK.assertEqual(reduced.columns(n), positions)
        CHECK.assertEqual(reduced.coefficients(n), [p + 1 for p in positions])


def test_native_offset_reduction_rejects_invalid_groups_atomically():
    """A bad later group cannot mutate the source or return partial output."""
    native = import_module("gana._native")
    rows = native.AffineRows.constants([1.25, -2.5])
    with CHECK.assertRaises(IndexError):
        rows.sum_python([[0], [2]])
    CHECK.assertEqual(rows.offsets(), [1.25, -2.5])
    large = native.AffineRows.constants([2**127 - 1])
    with CHECK.assertRaises(OverflowError):
        large.sum_python([[0, 0]])
