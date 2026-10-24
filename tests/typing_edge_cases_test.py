"""Exercise runtime edge cases exposed by the final typing repair batch."""

import operator

import numpy as np
import pytest
from matplotlib import pyplot as plt
from ppopt.solution import Solution as MPSolution

from gana import I, P, Prg, T, V
from gana.operators.composition import inf
from gana.utils.decorators import once
from gana.utils.draw import draw


@pytest.fixture
def vector_model():
    """Declare three columns so zero scaling must preserve multiple rows."""
    program = Prg()
    program.i = I(size=3)
    program.x = V(program.i)
    return program


@pytest.mark.parametrize("leq", [False, True])
@pytest.mark.parametrize("mode", ["multiply", "reflected", "divide"])
def test_zero_constraint_scaling_keeps_rows(vector_model, leq, mode):
    """A zero-scaled relation is valid at every original coordinate."""
    program = vector_model
    relation = program.x <= [2, 3, 4] if leq else program.x == [2, 3, 4]
    if mode == "multiply":
        scaled = relation * 0
    elif mode == "reflected":
        scaled = 0 * relation
    else:
        scaled = relation / float("inf")
    assert scaled.leq is leq
    assert len(scaled) == len(relation)
    assert [[v.n for v in row.variables] for row in scaled] == [
        [v.n for v in row.variables] for row in relation
    ]
    program.zero = scaled
    np.testing.assert_array_equal(program.A, np.zeros((3, 3)))
    np.testing.assert_array_equal(program.B, [0, 0, 0])


@pytest.mark.parametrize("reflected", [False, True])
def test_absent_constraint_multiplier_is_rejected(vector_model, reflected):
    """An absent operand cannot become a constraint with missing rows."""
    relation = vector_model.x <= 2
    with pytest.raises(TypeError, match="numeric operand"):
        if reflected:
            None * relation
        else:
            relation * None


@pytest.mark.parametrize("operation", [operator.mul, operator.truediv])
def test_constraint_operand_preserves_value_error(vector_model, operation):
    """Retain the user's exception contract for constraint operands."""
    relation = vector_model.x <= 2
    with pytest.raises(ValueError, match=r"Cannot .* constraints"):
        operation(relation, relation)


@pytest.mark.parametrize("kind", [P, V])
def test_singleton_grouped_index_formats(vector_model, kind):
    """A one-domain union must not be indexed as a positional sequence."""
    program = vector_model
    program.values = kind(program.i, **({"_": [1, 2, 3]} if kind is P else {}))
    element = program.values
    # Grouped metadata is the union-of-products form used after owner growth.
    element.index = {(program.i,)}
    assert element.index_ltx == f"({program.i.ltx})"
    assert element.longname == "values(i)"


@pytest.mark.parametrize("kind", ["line", "bar"])
def test_plot_missing_values_as_gaps(vector_model, kind):
    """Missing solution columns keep their positions without list mutation."""
    values = [0, None, 2]
    try:
        draw(vector_model.x, values, kind=kind, usetex=False, str_idx_lim=0)
        axis = plt.gca()
        plotted = (
            axis.lines[0].get_ydata(orig=False)
            if kind == "line"
            else [bar.get_height() for bar in axis.patches]
        )
        np.testing.assert_equal(plotted, [0, np.nan, 2])
        assert values == [0, None, 2]
    finally:
        plt.close("all")


def test_once_marker_can_be_removed_and_false_marker_still_blocks():
    """Keep the observable marker's existence-based behavior and reset hook."""
    calls = []

    @once
    def operation():
        """Count real invocations independently of the marker value."""
        calls.append(1)
        return len(calls)

    assert operation() == 1
    operation.has_run = False
    assert operation() is None
    del operation.has_run
    assert operation() == 2


def test_once_failure_still_sets_marker():
    """A failing first invocation remains consumed, as before this repair."""

    @once
    def operation():
        """Fail after the wrapper has installed its marker."""
        message = "expected failure"
        raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="expected failure"):
        operation()
    assert operation() is None


def test_missing_critical_region_does_not_record_evaluation():
    """Absent PPOPT results fail before populating model or member history."""
    program = Prg()
    program.x = V()
    program.t = T(_=(0, 1))
    program.bound = program.x >= program.t
    program.objective = inf(program.x)
    program.solutions[0] = MPSolution(program.ppopt(), [])
    with pytest.raises(TypeError, match="No solution exists"):
        program.eval(2)
    assert program.evaluation == {}
    assert program.n_evaluation == {}
    assert all(variable.evaluation == {} for variable in program.variables)
