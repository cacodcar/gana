"""Continuous Variable
"""

from __future__ import annotations

from itertools import product
from math import prod
from typing import Self, TYPE_CHECKING

from IPython.display import Math
from pyomo.environ import (
    Binary,
    Integers,
    NonNegativeIntegers,
    NonNegativeReals,
    Reals,
    Var,
)
from sympy import Idx, IndexedBase, Symbol, symbols

from .constraint import C
from .function import F
from .index import I
from .thing import X


if TYPE_CHECKING:
    from .parameter import P


class V:
    """A Continuous Variable"""

    def __init__(
        self,
        *index: I | X,
        name: str = 'contvar',
        itg: bool = False,
        nn: bool = True,
        bnr: bool = False,
    ):
        self.index = list(index)
        self.indices = prod(self.index)._
        self._: list[int | float] = None
        # This works well for variables generated at the indices
        # of a variable set
        self.name = name
        # if the variable is an integer variable
        self.itg = itg
        # if the variable is binary
        self.bnr = bnr
        if self.bnr:
            self.itg = bnr
            if not nn:
                raise ValueError('Binary variables must be non-negative')

        # if the variable is non negative
        self.nn = nn

        # value is determined when mathematical model is solved
        # the flag _fixed is changed when .fix(val) is called
        self._fixed = False
        self._: list[Self] = []

        # keeps a count of, updated in program
        self.count: int = None

        # if a variable is declared as a child (at an constituent index)
        # the mum is the parent variable
        self.mum = None

    def fix(self, values: P | list[float]):
        """Fix the value of the variable"""
        # i am not running a type check for Parameter here
        # P imports V
        if isinstance(values, list):
            self._ = values
            self._fixed = True
        else:
            self._ = values._
            self._fixed = True

    def idx(self) -> list[tuple]:
        """index"""
        return list(product(*[i._ if isinstance(i, I) else [i] for i in self.index]))

    def latex(self) -> str:
        """LaTeX representation"""
        return str(self) + r'_{' + ', '.join(rf'{m}' for m in self.index) + r'}'

    def sympy(self) -> IndexedBase | Symbol:
        """symbolic representation"""
        return IndexedBase(str(self))[
            symbols(",".join([f'{d}' for d in self.index]), cls=Idx)
        ]

    def pyomo(self) -> Var:
        """Pyomo representation"""
        idx = [i.pyomo() for i in self.index]

        if self.bnr:
            return Var(*idx, domain=Binary, doc=str(self))

        elif self.itg:
            if self.nn:
                return Var(*idx, domain=NonNegativeIntegers, doc=str(self))
            else:
                return Var(*idx, domain=Integers, doc=str(self))

        else:
            if self.nn:
                return Var(*idx, domain=NonNegativeReals, doc=str(self))
            else:
                return Var(*idx, domain=Reals, doc=str(self))

    def mps(self) -> str:
        """MPS representation"""
        return str(self).upper()

    def lp(self) -> str:
        """LP representation"""
        return str(self)

    def __len__(self):
        return prod([len(i) if isinstance(i, I) else 1 for i in self.index])

    def __getitem__(self, key: int | tuple):
        if isinstance(key, (int, slice)):
            return self._[key]

        return self._[
            [tuple([i.name for i in idx]) for idx in self.idx()].index(tuple(key))
        ]

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __neg__(self):
        return F(rel='-', two=self)

    def __pos__(self):
        return F(rel='+', two=self)

    def __add__(self, other: Self | F):
        return F(one=self, rel='+', two=other)

    def __radd__(self, other: Self | F):
        if other == 0:
            return self
        return self + other

    def __sub__(self, other: Self | F):

        return F(one=self, two=other, rel='-')

    def __rsub__(self, other: Self | F | int):
        if other == 0:
            return -self
        else:
            return -self + other

    def __mul__(self, other: Self | F):

        return F(one=self, two=other, rel='×')

    def __rmul__(self, other: Self | F | int):
        if other == 1:
            return self
        else:
            return self * other

    def __truediv__(self, other: Self | F):
        return F(one=self, two=other, rel='÷')

    def __rtruediv__(self, other: Self | F | int):
        if other == 1:
            return self
        else:
            return self / other

    def __iter__(self):
        for i in self._:
            yield i

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

    def __call__(self) -> str:
        return Math(self.latex())
