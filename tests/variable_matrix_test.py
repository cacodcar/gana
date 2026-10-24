"""Scalar and collection coefficient mappings must not recurse or alias."""

import operator

import pytest

from gana import I, Prg, V
from gana.sets.constraint import C


def test_unregistered_variable_matrix_is_empty():
    """An unregistered root has no populated coefficient rows."""
    assert V().matrix == {}


@pytest.mark.parametrize("indexed", [False, True])
def test_variable_collection_matrix(indexed):
    """Registered roots map each member to its own scalar coefficient row."""
    program = Prg()
    program.i = I(size=3)
    program.x = V(program.i) if indexed else V()
    members = list(program.x)
    expected = {member: {member.n: 1} for member in members}
    actual = program.x.matrix
    assert actual == expected
    first = members[0]
    actual[first][first.n] = 9
    assert program.x.matrix == expected
    assert first.matrix == {first.n: 1}


def test_selected_variable_matrix():
    """Selected rows retain global model column IDs and omit other rows."""
    program = Prg()
    program.i = I(size=4)
    program.x = V(program.i)
    selected = program.x(program.i[1:3])
    expected = {member: {member.n: 1} for member in selected}
    assert selected.matrix == expected
    assert len(expected) == 2


@pytest.mark.parametrize(
    ("operation", "message"),
    [
        (operator.mul, "Cannot multiply constraints"),
        (operator.truediv, "Cannot divide constraints"),
    ],
)
def test_constraint_type_errors_preserve_value_error(operation, message):
    """Retain the explicitly selected public exception class and messages."""
    program = Prg()
    program.x = V()
    left = C(program.x, leq=True)
    right = C(program.x, leq=True)
    with pytest.raises(ValueError, match=message):
        operation(left, right)
