"""Operators"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..sets.cases import Elem, FCase
from itertools import islice
from ..sets.function import F

if TYPE_CHECKING:
    from ..sets.index import I
    from ..sets.variable import V


def sigma(variable: V, over: I = None, position: int = None, neg: bool = False) -> F:
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

        if neg:
            f = -_variables[0] - _variables[1]

        else:
            f = _variables[0] + _variables[1]

        return f

    issumhow = (variable(), over, position)

    if neg:
        f = F(
            one=-_variables[0],
            sub=True,
            two=_variables[1],
            issumhow=issumhow,
        )
        for v in islice(_variables, 2, None):
            f = F(
                one=f,
                sub=True,
                two=v,
                one_type=Elem.F,
                two_type=Elem.V,
                issumhow=issumhow,
            )

        case = FCase.NEGSUM
        a = -1
    else:

        f = F(
            one=_variables[0],
            add=True,
            two=_variables[1],
            issumhow=issumhow,
        )

        for v in islice(_variables, 2, None):
            f = F(
                one=f,
                add=True,
                two=v,
                one_type=Elem.F,
                two_type=Elem.V,
                issumhow=issumhow,
            )
            # f += v

        # other options for looping,
        # all avoid recurssion

        # for i in range(2, len(_variables)):
        #     f += _variables[i]

        # for v in _variables[2:]:
        #     f += v

        case = FCase.SUM
        a = 1

    f.variables = _variables
    # f.one_type = Elem.F
    # f.two_type = Elem.V
    f.case = case
    f.rhs_thetas = []
    length_var = len(_variables[0])

    keys = list(zip(*(v.map for v in f.variables)))

    f.A = [[a] * length for _ in range(length_var)]

    for n in range(length_var):
        # make the child functions
        f_child = F()

        f_child.variables = [v[n] for v in f.variables]
        f_child.X = [v.n for v in f_child.variables]
        f_child.A = [a] * length

        key = keys[n]

        f_child.issumhow = (variable[length * n], over, position)

        f_child.case = case
        f_child.rhs_thetas = []
        f.X.append(f_child.X)
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
