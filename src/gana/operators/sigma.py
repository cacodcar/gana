"""Operators"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..sets.cases import Elem, FCase
from itertools import product
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

        if position == 0:
            # if this is the first index
            _variables = [variable(_index, *variable.index[1:]) for _index in over]

        if position == len(variable.index) - 1:
            # if this is the last index
            _variables = [variable(*variable.index[:-1], _index) for _index in over]

        else:
            # it is somewhere in the middle
            _variables = [
                variable(
                    *variable.index[:position], _index, *variable.index[position + 1 :]
                )
                for _index in over
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

    if neg:
        f = F(
            one=-_variables[0],
            sub=True,
            two=_variables[1],
            issumhow=(variable(), over, position),
        )
        for v in _variables[2:]:
            f -= v

        case = FCase.NEGSUM
        a = -1
    else:
        f = F(
            one=_variables[0],
            add=True,
            two=_variables[1],
            issumhow=(variable(), over, position),
        )

        for v in _variables[2:]:
            f += v
        case = FCase.SUM
        a = 1
    f.variables = _variables
    # f.one_type = Elem.F
    # f.two_type = Elem.V
    f.case = case
    f.rhs_thetas = []
    length_var = len(_variables[0])

    keys = list(zip(*[v.map for v in f.variables]))

    f.A = [[a] * length] * length_var

    for n in range(length_var):
        # make the child functions
        f_child = F()

        f_child.variables = [v[n] for v in f.variables]
        f_child.A = [a] * length
        f_child.X = [v.n for v in f_child.variables]

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

    # f.A = [[1] * length] * len(_variables[0])
    # f._ = []

    # for i in zip(*maps):
    #     print(i)

    # keys = [v.map.keys() for v in f.variables]
    # values = [v.map.values() for v in f.variables]

    # keys_ = []
    # values_ = []
    # for i in zip(*keys):
    #     keys_.append(i)
    # for i in zip(*values):
    #     values_.append(sum(i))

    # f.map = {k: v for k, v in zip(keys_, values_)}

    # for f_child in f._:
    #     f_child.parent = f
    #     f_child.one_type = Elem.F
    #     f_child.two_type = Elem.V
    #     f_child.case = case
    #     f_child.issumhow = (variable.copy(), variable.index, position)

    return f

    # if over is None:
    #     f_lhs = None
    #     for v in variable[:-1]:
    #         f_lhs += v
    #     f = f_lhs + variable[-1]
    #     f.one_type = Elem.F
    #     f.two_type = Elem.V
    #     f.case = FCase.SUM
    #     f.issumhow = (variable.copy(), over, position)
    #     for f_child in f._:
    #         f_child.one_type = Elem.F
    #         f_child.two_type = Elem.V
    #         f_child.case = FCase.SUM
    #     return f

    # if not position:
    #     position = variable.index.index(over)

    # if position == 0:
    #     # if this is the first index
    #     _variables = [variable(_index, *variable.index[1:]) for _index in over]
    # if position == len(variable.index) - 1:
    #     # if this is the last index
    #     _variables = [variable(*variable.index[:-1], _index) for _index in over]

    # else:
    #     # it is somewhere in the middle
    #     _variables = [
    #         variable(
    #             *variable.index[:position], _index, *variable.index[position + 1 :]
    #         )
    #         for _index in over
    #     ]

    # if len(over) == 2:
    #     # this is essentially just v_0 + v_1
    #     f = _variables[0] + _variables[1]
    #     f.one_type = Elem.V
    #     f.two_type = Elem.V
    #     f.case = FCase.SUM
    #     f.issumhow = (variable.copy(), over, position)
    #     for f_child in f._:
    #         f_child.one_type = Elem.V
    #         f_child.two_type = Elem.V
    #         f_child.case = FCase.SUM
    #     return f

    # f_lhs = None

    # if neg:
    #     for v in _variables[:-1]:
    #         f_lhs -= v

    #     f = f_lhs - _variables[-1]
    #     f.one_type = Elem.F
    #     f.two_type = Elem.V
    #     f.case = FCase.NEGSUM
    #     f.issumhow = (variable.copy(), over, position)
    #     for f_child in f._:
    #         f_child.one_type = Elem.F
    #         f_child.two_type = Elem.V
    #         f_child.case = FCase.NEGSUM
    #     return f

    # for v in _variables[:-1]:
    #     f_lhs += v
    # f = f_lhs + _variables[-1]
    # f.one_type = Elem.F
    # f.two_type = Elem.V
    # f.case = FCase.SUM
    # f.issumhow = (variable.copy(), over, position)
    # for f_child in f._:
    #     f_child.one_type = Elem.F
    #     f_child.two_type = Elem.V
    #     f_child.case = FCase.SUM
    # return f
