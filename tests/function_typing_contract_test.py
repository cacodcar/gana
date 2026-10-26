"""Public evaluation and arithmetic contracts behind expression annotations."""

import pytest

from gana import I, Prg, V


@pytest.fixture
def expression():
    """Build two rows of 2*x + y, with distinct model columns per row."""
    program = Prg()
    program.i = I(size=2)
    program.x = V(program.i)
    program.y = V(program.i)
    return 2 * program.x + program.y


def test_scalar_evaluation(expression):
    """A scalar row accepts positional values and returns one number."""
    assert expression[0].eval(3, 4) == 10


def test_collection_evaluation(expression):
    """One sequence of per-row values produces numbers in row order."""
    assert expression.eval([[3, 4], [5, 6]]) == [10, 16]


def test_collection_evaluation_preserves_arity_error(expression):
    """Multiple argument vectors retain the established unpacking failure."""
    with pytest.raises(ValueError, match="too many values to unpack"):
        expression.eval([3, 5], [4, 6])


@pytest.mark.parametrize("operand", [0, None])
def test_scaling_special_results(expression, operand):
    """Scaling keeps the numerical zero and absent-operand results."""
    result = expression * operand
    if operand is None:
        assert result is None
    else:
        assert type(result) is int
        assert result == 0


@pytest.mark.parametrize("operand", [None, (1, 2)])
def test_invalid_divisor_preserves_type_error(expression, operand):
    """Unsupported reciprocal operands retain Python's TypeError."""
    with pytest.raises(TypeError):
        expression / operand
