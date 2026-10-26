"""Alignment contracts for legacy collections and scalar expression members."""

from unittest import TestCase

import numpy as np
import pytest

from gana import I, P, Prg, V
from gana.sets.function import F

CHECK = TestCase()


class Rows:
    """Keep independent value and key orders to detect reindexing."""

    def __init__(self, label, count):
        """Keep mutable identities and reverse insertion-ordered keys."""
        self.label = label
        self.index = (label,)
        self._ = [{"position": position} for position in range(count)]
        self.map = {
            f"{label}{position}": self._[position]
            for position in reversed(range(count))
        }

    def __len__(self):
        """Use collection length for both size and ordinary truth testing."""
        return len(self._)

    def __str__(self):
        """Give incompatibility diagnostics a stable operand label."""
        return self.label


def expression(left, right, parent=None):
    """Isolate alignment from normalization and matrix generation."""
    result = object.__new__(F)
    result.one, result.two, result.parent = left, right, parent
    return result


def check_rows(values, keys, source, positions, shared):
    """Check exact order, shared members and unchanged collection aliases."""
    CHECK.assertEqual(values, [source._[position] for position in positions])
    CHECK.assertTrue(
        all(
            value is source._[position]
            for value, position in zip(values, positions)
        ),
    )
    CHECK.assertEqual(list(keys), [list(source.map)[p] for p in positions])
    CHECK.assertEqual(values is source._, shared)
    CHECK.assertEqual(keys is source.map, shared)


@pytest.mark.parametrize(
    "left_size,right_size,mismatch,left_positions,"
    "right_positions,left_shared,right_shared",
    [
        (1, 1, 0, [0], [0], True, True),
        (2, 2, 0, [0, 1], [0, 1], True, True),
        (4, 2, -2, [0, 1, 2, 3], [0, 0, 1, 1], True, False),
        (2, 4, 2, [0, 0, 1, 1], [0, 1, 2, 3], False, True),
        (1, 3, 3, [0, 0, 0], [0, 1, 2], False, True),
        (3, 1, -3, [0, 1, 2], [0, 0, 0], True, False),
        (2, 6, 3, [0, 0, 0, 1, 1, 1], [0, 1, 2, 3, 4, 5], False, True),
        (6, 2, -3, [0, 1, 2, 3, 4, 5], [0, 0, 0, 1, 1, 1], True, False),
    ],
)
def test_collection_alignment(
    *,
    left_size,
    right_size,
    mismatch,
    left_positions,
    right_positions,
    left_shared,
    right_shared,
):
    """Preserve signed mismatch and consecutive operand repetition."""
    left, right = Rows("left", left_size), Rows("right", right_size)
    result = expression(left, right)
    result.handle_mismatch()
    CHECK.assertEqual(result.mis, mismatch)
    CHECK.assertIs(result.one, left)
    CHECK.assertIs(result.two, right)
    check_rows(result._one, result._one_map, left, left_positions, left_shared)
    check_rows(
        result._two,
        result._two_map,
        right,
        right_positions,
        right_shared,
    )


@pytest.mark.parametrize("left_size,right_size", [(2, 3), (3, 2), (4, 6)])
def test_incompatible_alignment_is_atomic(left_size, right_size):
    """Reject nondivisible lengths before overwriting prior alignment state."""
    left, right = Rows("left", left_size), Rows("right", right_size)
    result = expression(left, right)
    original = object()
    for name in ("mis", "_one", "_two", "_one_map", "_two_map"):
        setattr(result, name, original)
    with pytest.raises(ValueError) as error:
        result.handle_mismatch()
    CHECK.assertEqual(
        str(error.value),
        f"left with index ('left',) (length = {left_size}) and "
        f"right with ('right',) (length = {right_size}) are not compatible",
    )
    for name in ("mis", "_one", "_two", "_one_map", "_two_map"):
        CHECK.assertIs(getattr(result, name), original)


@pytest.mark.parametrize("scalar", [None, 0, -0.0, 2.5, False, True])
@pytest.mark.parametrize("reverse", [False, True])
def test_parented_scalar_uses_symbolic_map(scalar, reverse):
    """Numeric/None operands borrow the opposite map, including signed zero."""
    rows = Rows("symbol", 2)
    left, right = (rows, scalar) if reverse else (scalar, rows)
    result = expression(left, right, parent=object())
    result.handle_mismatch()
    CHECK.assertEqual(result.mis, 0)
    CHECK.assertIs(result._one[0], left)
    CHECK.assertIs(result._two[0], right)
    CHECK.assertIs(result._one_map, rows.map)
    CHECK.assertIs(result._two_map, rows.map)


@pytest.mark.parametrize(
    "left_size,right_size,parented",
    [
        (0, 2, False),
        (2, 0, False),
        (0, 0, False),
        (0, 2, True),
        (2, 0, True),
        (0, 0, True),
        (2, 3, True),
    ],
)
def test_empty_or_parented_collections_keep_scalar_wrapping(
    left_size,
    right_size,
    parented,
):
    """Keep original maps for empty roots and parented rows."""
    left, right = Rows("left", left_size), Rows("right", right_size)
    result = expression(left, right, object() if parented else None)
    result.handle_mismatch()
    CHECK.assertEqual(result.mis, 0)
    CHECK.assertIs(result._one[0], left)
    CHECK.assertIs(result._two[0], right)
    CHECK.assertIs(result._one_map, left.map)
    CHECK.assertIs(result._two_map, right.map)


@pytest.mark.parametrize("reverse", [False, True])
def test_multiscale_subtraction_numeric_oracle(reverse):
    """Repeat coarse parameters consecutively in end-to-end matrices."""
    program = Prg()
    program.fine = I(size=4)
    program.coarse = I(size=2)
    program.x = V(program.fine)
    program.rate = P(program.coarse, _=[2, 3])
    value = program.rate - program.x if reverse else program.x - program.rate
    constraint_limit = 10
    program.c = value <= constraint_limit
    sign = -1 if reverse else 1
    np.testing.assert_array_equal(program.A, sign * np.eye(4))
    expected = [8, 8, 7, 7] if reverse else [12, 12, 13, 13]
    np.testing.assert_array_equal(program.B, expected)
