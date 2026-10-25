"""Operators"""

from __future__ import annotations

from importlib import import_module
from itertools import product

# from itertools import islice
from typing import TYPE_CHECKING

from gana.types import Number

from ..sets.cases import Elem, FCase
from ..sets.function import F
from ..sets.rows import sum_expression

if TYPE_CHECKING:
    from ..sets.index import I
    from ..sets.variable import V


def _determine_index(variable, over, position):
    """Select V columns for a whole-set or one-axis reduction."""
    variable_index = tuple(variable.index)
    if over:
        length = len(over)

        if not position:
            position = variable_index.index(over)

        # Precompute slices
        before = variable_index[:position]
        next_axis = position + 1
        after = variable_index[next_axis:]

        # Build variables
        _variables = [
            variable(*before, _index, *after, make_new=True) for _index in over
        ]

    else:
        # sum over the entire set
        _variables = variable._
        length = len(variable)
        position = None
        over = variable.index

    return _variables, over, length, position


def _output_layout(variable, position):
    """Describe the coordinates left after reducing a variable set."""
    axes = tuple(variable.index)
    if position is None:
        axes = ()
    else:
        after = position + 1
        axes = axes[:position] + axes[after:]
    return axes, tuple(product(*axes))


def _birth_parent(variable, _variables, over, position, length):
    """Build the compact V-sum container with its remaining output axes."""
    _f = F()
    _f.case = FCase.SUM
    _f.issumhow = (variable.copy(), over, position)
    _f.variables = _variables
    _f.index = tuple(v.index for v in _f.variables)
    _f.one = _f
    _f.one_type = Elem.F
    _f.give_name()

    _f._row_layout = _output_layout(variable, position)
    _f.rhs_thetas = []
    length_var = len(_variables[0])
    keys = list(zip(*(v.map for v in _f.variables)))
    coefficients: list[list[Number]] = [
        [1] * length for _ in range(length_var)
    ]
    _f.A = coefficients
    return _f, length_var, keys


def _birth_children(f, length_var, keys, *, variable, over, position, length):
    """Build unit-weight scalar rows with stable term order and positions."""
    for n in range(length_var):
        # make the child functions
        f_child = F()
        f_child.variables = [v[n] for v in f.variables]
        f_child.P = [v.n for v in f_child.variables]
        coefficients: list[Number] = [1] * length
        f_child.A = coefficients
        key = keys[n]
        f_child.issumhow = (variable[length * n], over, position)
        f_child.parent = f
        f_child.pos = n
        f_child.case = FCase.SUM
        f_child.rhs_thetas = []
        f.P.append(f_child.P)
        f_child.give_name()
        f_child._ = [f_child]
        f._.append(f_child)
        f.map[key] = f_child
        f_child.map[key] = f_child
        f_child.index = key
        f_child.one = f_child
        f_child.one_type = Elem.F
    return f


def sigma(
    variable: V | F,
    over: I | None = None,
    position: int | None = None,
) -> F:
    """
    Summation without recursion, also allows better printing

    A whole-set reduction of a one-row expression returns that expression:
    its coefficients and constant already represent the complete sum.

    :param variable: variable set or expression
    :type variable: V | F
    :param over: over what index
    :type over: I | None
    :param position: zero-based position of the reduction axis, if needed.
    :type position: int | None

    :returns: summed up function
    :rtype: F
    """
    if (
        isinstance(variable, F)
        and len(variable) == 1
        and over is None
        and position is None
    ):
        return variable

    result = import_module("gana.backends.native.algebra").try_sum(
        variable,
        over,
        position,
    )
    if result is not None:
        return result

    if isinstance(variable, F):
        return sum_expression(variable, over, position)

    _variables, over, length, position = _determine_index(
        variable,
        over,
        position,
    )

    pair_terms = 2
    if length == pair_terms:
        # short-circuit for length 2
        # just v_0 + v_1
        result = _variables[0] + _variables[1]
        result._row_layout = _output_layout(variable, position)
        return result

    f, length_var, keys = _birth_parent(
        variable,
        _variables,
        over,
        position,
        length,
    )

    return _birth_children(
        f,
        length_var,
        keys,
        variable=variable,
        over=over,
        position=position,
        length=length,
    )
