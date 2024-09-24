"""Binary Variable
"""

from __future__ import annotations

from math import prod
from typing import Self, TYPE_CHECKING
from sympy import IndexedBase, Symbol, symbols, Idx
from ..relational.f import F
from ..relational.c import C

if TYPE_CHECKING:
    from .s import S


class X:
    """A Binary Variable"""

    def __init__(self, *args: S, name: str = 'bvar'):
        self.index = args
        self.name = name
        # value is determined when mathematical model is solved
        self.value = None

    def x(self):
        """returns the value of the variable"""
        return self.value

    @property
    def sym(self) -> IndexedBase | Symbol:
        """symbolic representation"""
        if self.index:
            return IndexedBase(self.name)[
                symbols(",".join([f'{d}' for d in self.index]), cls=Idx)
            ]
        else:
            return Symbol(self.name)

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __len__(self):
        return prod([len(s) for s in self.index])

    def __add__(self, other: Self | F):

        return F(one=self, two=other, rel='+')

    def __sub__(self, other: Self | F):

        return F(one=self, two=other, rel='-')

    def __mul__(self, other: Self | F):

        return F(one=self, two=other, rel='*')

    def __truediv__(self, other: Self | F):

        return F(one=self, two=other, rel='/')

    def __eq__(self, other):
        return C(lhs=self, rhs=other, rel='eq')

    def __le__(self, other):
        return C(lhs=self, rhs=other, rel='leq')

    def __ge__(self, other):
        return C(lhs=self, rhs=other, rel='geq')

    def __lt__(self, other):
        return self <= other

    def __gt__(self, other):
        return self >= other
