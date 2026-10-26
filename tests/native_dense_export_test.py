"""Exact dense values, empty shapes and detached mutable Python row lists."""

from importlib import import_module
from unittest import TestCase

import pytest

from gana import I, Prg, T, V

CHECK = TestCase()


@pytest.mark.parametrize(("rows", "columns"), [(0, 0), (0, 5), (3, 0), (3, 5)])
def test_empty_dense_shapes_and_independent_rows(rows, columns):
    """Empty rows keep their shape and never share mutable list storage."""
    native = import_module("gana._native")
    batch = native.AffineRows([([], [], 0) for _ in range(rows)])
    compiled = native.SparseRows([batch], columns)
    expected = [[0] * columns for _ in range(rows)]
    result = compiled.dense()
    CHECK.assertEqual(compiled.shape, (rows, columns))
    CHECK.assertEqual(result, expected)
    CHECK.assertIs(type(result), list)
    for row in result:
        CHECK.assertIs(type(row), list)
    CHECK.assertEqual(len({id(row) for row in result}), rows)
    if rows:
        result[0].append(99)
        CHECK.assertEqual(result[1:], expected[1:])
    result.append([99])
    CHECK.assertEqual(compiled.dense(), expected)


def test_dense_number_kinds_cancellation_and_detachment():
    """Keep large integers and explicit float zeros without float coercion."""
    native = import_module("gana._native")
    large = 2**120 + 1
    ids = [(0, n, column) for n, column in enumerate([0, 1, 2, 3, 4, 4])]
    batch = native.AffineRows(
        [(ids, [large, -large, 1.5, 0.0, 2.5, -2.5], 0)],
    )
    compiled = native.SparseRows([batch, batch], 6)
    expected = [large, -large, 1.5, 0.0, 0.0, 0]
    result = compiled.dense()
    CHECK.assertEqual(result, [expected, expected])
    CHECK.assertEqual(
        [type(value) for value in result[0]],
        [int, int, float, float, float, int],
    )
    result[0][0] = 99
    result[1].clear()
    CHECK.assertEqual(compiled.dense(), [expected, expected])
    CHECK.assertEqual(compiled.parts()[0][:5], expected[:5])


def test_public_dense_exports_remain_detached_after_growth():
    """Both column spaces expand independently without changing old exports."""
    p = Prg()
    p.i = I("a", "b")
    p.x = V(p.i, mutable=True)
    p.c = p.x + p.x <= T(p.i, _=(0, 3))
    before_a, before_f = p.A, p.F
    CHECK.assertEqual(before_a, [[2, 0], [0, 2]])
    CHECK.assertEqual(before_f, [[1, 0], [0, 1]])
    before_a[0][0], before_f[1][1] = 99, 99
    p.j = I("c")
    p.x = V(p.j)
    p.extra = T(p.j, _=(0, 4))
    CHECK.assertEqual(p.A, [[2, 0, 0], [0, 2, 0]])
    CHECK.assertEqual(p.F, [[1, 0, 0], [0, 1, 0]])
    CHECK.assertEqual(before_a, [[99, 0], [0, 2]])
    CHECK.assertEqual(before_f, [[1, 0], [0, 99]])
