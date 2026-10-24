"""Direct native interval ingestion keeps detached values and atomic owners."""

import sys
from fractions import Fraction
from importlib import import_module
from math import copysign, inf
from unittest import TestCase

import pytest

from gana.indexing.coordinates import encode_bounds
from gana.storage.parameters import NATIVE

pytestmark = pytest.mark.skipif(not NATIVE, reason="native bound ingestion")
CHECK = TestCase()


@pytest.mark.parametrize("cartesian", [False, True])
def test_native_batch_detaches_and_survives_its_input(cartesian):
    """Exact endpoints and signed zero outlive input edits and the batch."""
    native = import_module("gana._native")
    rows = [(2**100, 2**100 + 1), (-inf, -0.0), (Fraction(-3, 2), True)]
    batch = native.prepare_bounds(rows, encode_bounds)
    rows[:] = [(8, 9)]
    constructor = (
        native.MemberTable.cartesian if cartesian else native.MemberTable
    )
    keys = [[0, 1, 2]] if cartesian else [[0], [1], [2]]
    table = constructor(keys, [7, 8, 9], batch)
    del batch
    CHECK.assertEqual(
        table.bounds(0),
        ((str(2**100), 0.0), (str(2**100 + 1), 0.0)),
    )
    CHECK.assertEqual(table.bounds(2), (("", -1.5), ("1", 0.0)))
    CHECK.assertEqual(copysign(1, table.bounds(1)[1][1]), -1)
    CHECK.assertEqual(table.number(2), 9)


@pytest.mark.parametrize("prepared", [False, True])
def test_native_append_failure_keeps_batch_and_owner_usable(prepared):
    """Length and duplicate-key failures leave the owner and batch usable."""
    native = import_module("gana._native")
    table = native.MemberTable([[0]], [0], [encode_bounds((0, 1))])
    rows = [(2, 3), (4, 5)]
    batch = (
        native.prepare_bounds(rows, encode_bounds)
        if prepared
        else [encode_bounds(pair) for pair in rows]
    )
    original = table.export()
    with pytest.raises(ValueError):
        table.append([[1], [2]], [1], batch)
    CHECK.assertEqual(table.export(), original)
    with pytest.raises(IndexError):
        table.append([[1], [0]], [1, 2], batch)
    CHECK.assertEqual(table.export(), original)
    table.append([[1], [2]], [1, 2], batch)
    other = native.MemberTable([[8], [9]], [8, 9], batch)
    table.set_bounds(1, encode_bounds((10, 11)))
    CHECK.assertEqual(other.bounds(0), encode_bounds((2, 3)))
    CHECK.assertEqual(table.bounds(1), encode_bounds((10, 11)))


class ObservedFloat(float):
    """Endpoint conversion reads its owner before optionally failing."""

    def __float__(self):
        """Exercise unlocked callbacks and propagate the original failure."""
        self.seen.append(self.table.export())
        if self.refuse:
            message = "conversion refused"
            raise ValueError(message)
        return super().__float__()


def test_fallback_is_ordered_unlocked_and_failure_is_atomic():
    """Callbacks can read the owner; a late failure prevents any append."""
    native = import_module("gana._native")
    table = native.MemberTable([[0]], [0], [None])
    observed = ObservedFloat(2)
    observed.table, observed.seen, observed.refuse = table, [], True
    seen = []

    def fallback(pair):
        """Record fallback order, stopping at the first failed conversion."""
        seen.append(pair)
        return encode_bounds(pair)

    with pytest.raises(ValueError, match="conversion refused"):
        native.prepare_bounds([(1, 2), (observed, 3), (False, True)], fallback)
    CHECK.assertEqual(len(seen), 1)
    CHECK.assertEqual(observed.seen, [table.export()])
    CHECK.assertEqual(len(table), 1)
    observed.refuse = False
    batch = native.prepare_bounds([(observed, 3), None], fallback)
    table.append([[1], [2]], [1, 2], batch)
    CHECK.assertEqual(table.bounds(1), (("", 2.0), ("3", 0.0)))
    CHECK.assertIsNone(table.bounds(2))


def test_repeated_bounds_keep_independent_rows_and_owners():
    """Repeated bounds survive batch release and independent edits."""
    native = import_module("gana._native")
    pair = (2**100, 2**100 + 1)
    references = sys.getrefcount(pair)
    batch = native.prepare_bounds([pair] * 4, encode_bounds)
    CHECK.assertEqual(sys.getrefcount(pair), references)
    first = native.MemberTable.cartesian([[0, 1, 2, 3]], list(range(4)), batch)
    second = native.MemberTable([[0], [1], [2], [3]], list(range(4)), batch)
    del batch
    first.set_bounds(1, encode_bounds((-4, 5)))
    second.set_bounds(2, encode_bounds((6, 7)))
    CHECK.assertEqual(first.bounds(1), encode_bounds((-4, 5)))
    CHECK.assertEqual(second.bounds(2), encode_bounds((6, 7)))
    for row in (0, 2, 3):
        CHECK.assertEqual(first.bounds(row), encode_bounds(pair))
    for row in (0, 1, 3):
        CHECK.assertEqual(second.bounds(row), encode_bounds(pair))


def test_repeated_custom_endpoints_are_converted_every_time():
    """A repeated subclass tuple invokes both conversions for every row."""
    native = import_module("gana._native")
    observed = ObservedFloat(2)
    observed.table = native.MemberTable([[0]], [0], [None])
    observed.seen, observed.refuse = [], False
    pair = (observed, observed)
    batch = native.prepare_bounds([pair] * 3, encode_bounds)
    table = native.MemberTable([[0], [1], [2]], [0, 1, 2], batch)
    CHECK.assertEqual(len(observed.seen), 6)
    CHECK.assertEqual(table.bounds(2), (("", 2.0), ("", 2.0)))


def test_equal_bounds_preserve_endpoint_types_and_zero_signs():
    """Numerical equality cannot merge integer, float or signed-zero pairs."""
    native = import_module("gana._native")
    negative, positive, integer = (-0.0, 1.0), (0.0, 1.0), (0, 1)
    rows = [negative, negative, positive, positive, integer, integer]
    batch = native.prepare_bounds(rows, encode_bounds)
    table = native.MemberTable(
        [[row] for row in range(6)],
        list(range(6)),
        batch,
    )
    CHECK.assertEqual(table.bounds(4), (("0", 0.0), ("1", 0.0)))
    CHECK.assertEqual(table.bounds(2), (("", 0.0), ("", 1.0)))
    CHECK.assertEqual(copysign(1, table.bounds(0)[0][1]), -1)
    CHECK.assertEqual(copysign(1, table.bounds(2)[0][1]), 1)


@pytest.mark.parametrize("iterator", [False, True])
def test_conversion_settings_changes_are_not_hidden_by_reuse(iterator):
    """Callbacks and iterator steps can change later integer conversion."""
    native = import_module("gana._native")
    pair = (10**700, 10**700 + 1)
    original = sys.get_int_max_str_digits()

    def fallback(value):
        """Restrict conversion after the first accepted primitive interval."""
        sys.set_int_max_str_digits(640)
        return encode_bounds(value)

    def generate():
        """Change settings between two occurrences of the exact same tuple."""
        yield pair
        sys.set_int_max_str_digits(640)
        yield pair

    try:
        sys.set_int_max_str_digits(0)
        values = generate() if iterator else [pair, None, pair]
        with pytest.raises(ValueError, match="integer string conversion"):
            native.prepare_bounds(values, fallback)
    finally:
        sys.set_int_max_str_digits(original)


@pytest.mark.parametrize("grow", [False, True])
def test_fallback_list_edits_preserve_python_iteration(grow):
    """Custom conversion can extend or shorten the remaining input list."""
    native = import_module("gana._native")
    pair = (1, 2)
    rows = [pair, None, pair]

    def fallback(value):
        """Modify the pending rows just as a Python list iterator observes."""
        rows[2:] = [pair, pair] if grow else []
        return encode_bounds(value)

    batch = native.prepare_bounds(rows, fallback)
    count = 4 if grow else 2
    table = native.MemberTable(
        [[row] for row in range(count)],
        list(range(count)),
        batch,
    )
    CHECK.assertEqual(len(table), count)
    CHECK.assertIsNone(table.bounds(1))
