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
    """Summation, allows better printing, avoids recurssion error

    Args:
        variable (V): variable set
        over (I): over what index
        position (int, optional): position of the index in the variable indices. Defaults to None.
        neg (bool, optional): if this is a negative sum. Defaults to False.
    Returns:
        F: summed up function
    """

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

    if length == 2:
        # this checks for v_0 + v_1
        return _variables[0] + _variables[1]

    f = F()

    f.case = FCase.SUM

    f.issumhow = (variable.copy(), over, position)

    f.variables = _variables
    f.index = tuple(v.index for v in f.variables)
    f.one = f
    f.one_type = Elem.F
    f.give_name()
    # f.two_type = Elem.V
    f.rhs_thetas = []
    
    length_var = len(_variables[0])

    keys = list(zip(*(v.map for v in f.variables)))

    f.A = [[1] * length for _ in range(length_var)]

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
