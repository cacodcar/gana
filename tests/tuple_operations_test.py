"""Preserve coordinate order and Python addition dispatch in tuple products."""

from math import prod

import pytest

from gana import I, V
from gana.sets.function import F


class NonIteratingTuple(tuple):
    """Expose accidental unpacking where tuple concatenation never iterated."""

    def __iter__(self):
        """Reject iteration while leaving built-in tuple addition available."""
        message = "Tuple addition must not invoke custom iteration"
        raise AssertionError(message)


class AdditionTuple(NonIteratingTuple):
    """Expose left and reflected addition without invoking iteration."""

    def __add__(self, other):
        """Return operands intact so identity and dispatch can be checked."""
        return "left", self, other

    def __radd__(self, other):
        """Distinguish reflected dispatch when this is the right operand."""
        return "right", other, self


@pytest.mark.parametrize("kind", [tuple, NonIteratingTuple])
def test_coordinate_order_and_identity(kind):
    """Prepending/appending preserves axes without traversing their members."""
    first, second, third = I(), I(), I()
    axes = kind((first, second))
    assert third * axes == (third, first, second)
    assert axes * third == (first, second, third)
    variable = V()
    result = axes * variable
    assert result[:2] == (first, second)
    assert result[-1] is variable


def test_empty_products_and_math_prod_identity():
    """Empty coordinate tuples and math.prod retain the same identity rules."""
    first, second, third = I(), I(), I()
    assert first * () == (first,)
    assert () * first == (first,)
    assert prod([first]) is first
    assert prod([first, second, third]) == (first, second, third)
    assert first * None is None
    assert None * first is None


def test_tuple_subclass_addition_dispatch():
    """Honor both tuple-subclass addition hooks in public products."""
    axis, variable = I(), V()
    axes = AdditionTuple((axis,))
    assert axis * axes == ("right", (axis,), axes)
    assert axes * axis == ("left", axes, (axis,))
    result = axes * variable
    assert result[0] == "left"
    assert result[1] is axes
    assert result[2][0] is variable


@pytest.mark.parametrize("operand", [[], "axis", 2])
def test_reflected_index_product_rejects_invalid_operands(operand):
    """Tuple unpacking must not start accepting arbitrary iterable operands."""
    with pytest.raises(TypeError):
        operand * I()


def sum_row(left_index):
    """Build the existing reduction-constructor path with concrete symbols."""
    left, right = F(), V()
    left.index = left_index
    right.index = (I(),)
    return F(one=left, two=right, add=True, issumhow=(right, None, None))


@pytest.mark.parametrize("kind", [tuple, NonIteratingTuple])
def test_reduction_coordinates_remain_nested(kind):
    """Append the second operand's whole coordinate tuple as one element."""
    first, second = I(), I()
    row = sum_row(kind((first, second)))
    assert row.index[:2] == (first, second)
    assert row.index[-1] is row.two.index


def test_reduction_preserves_tuple_subclass_addition():
    """Reduction construction retains a custom left tuple's addition result."""
    axes = AdditionTuple((I(),))
    row = sum_row(axes)
    assert row.index[0] == "left"
    assert row.index[1] is axes
    assert row.index[2][0] is row.two.index


@pytest.mark.parametrize("operand", [[], "axis", None])
def test_reduction_rejects_non_tuple_coordinates(operand):
    """Invalid coordinate containers retain their original TypeError."""
    with pytest.raises(TypeError):
        sum_row(operand)
