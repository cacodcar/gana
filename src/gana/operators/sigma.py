"""Operators"""

from __future__ import annotations

# from itertools import islice
from typing import TYPE_CHECKING

from ..sets.cases import Elem, FCase
from ..sets.function import F

if TYPE_CHECKING:
    from ..sets.index import I
    from ..sets.variable import V


def sigma(variable: V, over: I = None, position: int = None) -> F:
    """
    Summation without recursion, also allows better printing

    :param variable: variable set
    :type variable: V
    :param over: over what index
    :type over: I | None
    :param position: position of the index in the variable indices. Defaults to None.
    :type position: int | None

    :returns: summed up function
    :rtype: F
    """

    def _determine_index(over, position):
        if over:
            length = len(over)

            if not position:
                position = variable.index.index(over)

            # Precompute slices
            before = variable.index[:position]
            after = variable.index[position + 1 :]

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

    def _birth_parent(variable, _variables, over, position, length):
        _f = F()
        _f.case = FCase.SUM
        _f.issumhow = (variable.copy(), over, position)
        _f.variables = _variables
        _f.index = tuple(v.index for v in _f.variables)
        _f.one = _f
        _f.one_type = Elem.F
        _f.give_name()

        _f.rhs_thetas = []
        length_var = len(_variables[0])
        keys = list(zip(*(v.map for v in _f.variables)))
        _f.A = [[1] * length for _ in range(length_var)]
        return _f, length_var, keys

    def _birth_children(f, length_var, keys):
        for n in range(length_var):
            # make the child functions
            f_child = F()
            f_child.variables = [v[n] for v in f.variables]
            f_child.P = [v.n for v in f_child.variables]
            f_child.A = [1] * length
            key = keys[n]
            f_child.issumhow = (variable[length * n], over, position)
            f_child.parent = f
            f_child.case = FCase.SUM
            f_child.rhs_thetas = []
            f.P.append(f_child.P)
            f_child.give_name()
            f_child._ = [f_child]
            f._.append(f_child)
            f.map[key] = f_child
            f_child.map[key] = f_child
            f_child.parent = f
            f_child.index = key
            f_child.one = f_child
            f_child.one_type = Elem.F
        return f

    _variables, over, length, position = _determine_index(over, position)

    if length == 2:
        # short-circuit for length 2
        # just v_0 + v_1
        return _variables[0] + _variables[1]

    f, length_var, keys = _birth_parent(variable, _variables, over, position, length)

    return _birth_children(f, length_var, keys)
