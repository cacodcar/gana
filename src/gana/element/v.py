"""Continuous Variable
"""

from __future__ import annotations

from itertools import product
from math import prod
from typing import TYPE_CHECKING, Self

from sympy import Idx, IndexedBase, Symbol, symbols

from ..relational.c import C
from ..relational.f import F
# if TYPE_CHECKING:
from .s import S


class V:
    """A Continuous Variable"""

    def __init__(self, *args: S, name: str = 'contvar'):
        self.index = args
        self.name = name

        # value is determined when mathematical model is solved
        # the flag _fixed is changed when .fix(val) is called
        self._fixed = False
        self._: int | float = None
        self.val: dict = None
        # keeps a count of, updated in program
        self.count: int = None

        self.vset = {i: V(i, name=self.name) for i in self.idx}

    @property
    def sym(self) -> IndexedBase | Symbol:
        """symbolic representation"""
        if self.index:
            return IndexedBase(self.name)[
                symbols(",".join([f'{d}' for d in self.index]), cls=Idx)
            ]
        else:
            return Symbol(self.name)

    @property
    def idx(self) -> list[tuple]:
        """index"""
        return list(product(*[s.members for s in self.index if isinstance(s, S)]))

    def fix(self, val: float | list[float]):
        """Fix the value of the variable"""
        self._ = val
        if self.index:
            # values are attached to indices in a dictionary
            # this helps access for getitem etc
            self.val = {
                idx: self._[n]
                for n, idx in enumerate(list(product(*[s.members for s in self.index])))
            }
        else:
            # if list, just give positions as indices
            if isinstance(self._, list):
                self.val = {n: v for n, v in enumerate(self._)}
            # if single value (float), give it a zero index
            else:
                self.val = {0: self._}

        self._fixed = True

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __len__(self):
        return prod([len(s) for s in self.index])

    def __getitem__(self, key: int | tuple):
        if self._fixed:
            return self.val[key]
        else:
            if self.index:
                # if set of variables, return the variable at that key
                return self.vset[key]
            else:
                # do not return anything if not fixed
                print('TBD')

    def __neg__(self):
        return F(rel='-', two=self)

    def __pos__(self):
        return F(rel='+', two=self)

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
        return C(lhs=self, rhs=other, rel='le')

    def __ge__(self, other):
        return C(lhs=self, rhs=other, rel='ge')

    def __lt__(self, other):
        return self <= other

    def __gt__(self, other):
        return self >= other
