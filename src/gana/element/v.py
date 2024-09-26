"""Continuous Variable
"""

from itertools import product
from math import prod
from typing import Self

from sympy import Idx, IndexedBase, Symbol, symbols

from ..relational.c import C
from ..relational.f import F

from .s import S


class V:
    """A Continuous Variable"""

    def __init__(
        self, *args: S, name: str = 'contvar', itg: bool = False, nn: bool = True
    ):
        self.index = args
        self.name = name
        # if the variable is an integer variable
        self.itg = itg
        # if the variable is non negative
        self.nn = nn

        # value is determined when mathematical model is solved
        # the flag _fixed is changed when .fix(val) is called
        self._fixed = False
        self._ = None
        # keeps a count of, updated in program
        self.count: int = None

        # if a variable is declared as a child (at an constituent index)
        # the mum is the parent variable
        self.mum = None
        # these collect the variables that are generated at each index
        self.kids: list[Self] = []

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
        return list(
            product(*[s.members if isinstance(s, S) else [s] for s in self.index])
        )

    def fix(self, val: float | list[float]):
        """Fix the value of the variable"""
        self._ = val
        if self.index:
            # values are attached to indices in a dictionary
            # this helps access for getitem etc
            self._ = {idx: self._[n] for n, idx in enumerate(self.idx)}
        else:
            # if list, just give positions as indices
            if isinstance(self._, list):
                self._ = {n: v for n, v in enumerate(self._)}
            # if single value (float), give it a zero index
            else:
                self._ = {0: self._}

        self._fixed = True

    def __len__(self):
        return prod([len(s) if isinstance(s, S) else 1 for s in self.index])

    def __getitem__(self, key: int | tuple):
        if isinstance(key, tuple):
            k = self.idx.index(key)
        if isinstance(key, int):
            k = key
        if self._fixed:
            return self.kids[k]._
        else:
            return self.kids[k]

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __neg__(self):
        return F(rel='-', two=self)

    def __pos__(self):
        return F(rel='+', two=self)

    def __add__(self, other: Self | F):
        return F(one=self, two=other, rel='+')

    def __radd__(self, other: Self | F | int):
        if other == 0:
            return self
        else:
            return self.__add__(other)

    def __sub__(self, other: Self | F):

        return F(one=self, two=other, rel='-')

    def __mul__(self, other: Self | F):

        return F(one=self, two=other, rel='*')

    def __truediv__(self, other: Self | F):

        return F(one=self, two=other, rel='/')

    def __eq__(self, other):
        return C(lhs=+self, rhs=other, rel='eq')

    def __le__(self, other):
        return C(lhs=+self, rhs=other, rel='le')

    def __ge__(self, other):
        return C(lhs=+self, rhs=other, rel='ge')

    def __lt__(self, other):
        return self <= other

    def __gt__(self, other):
        return self >= other
