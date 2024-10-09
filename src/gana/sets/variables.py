"""Continuous Variable
"""

from __future__ import annotations

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

from .constraints import C
from .functions import F
from .indices import I
from ..elements.index import Idx
from .ordered import Set


if TYPE_CHECKING:
    from .parameters import P


class V(Set):
    """Variable Set"""

    def __init__(
        self,
        itg: bool = False,
        nn: bool = True,
        bnr: bool = False,
    ):
        self.index = list(index)

        self.name = name
        # variables generated at the indices
        # of a variable set are stored here
        # once realized, the values take a int or float value

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
        self._: list[int | float] = []
        # the flag _fixed is changed when .fix(val) is called
        self._fixed = False

        # tags for the members of the Variable set
        self.number: int = None

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
        if self.parent:
            return self.index
        else:
            return [(i,) if not isinstance(i, tuple) else i for i in prod(self.index)._]

    def latex(self) -> str:
        """LaTeX representation"""
        return str(self) + r'_{' + ', '.join(rf'{m}' for m in self.index) + r'}'

    def pprint(self) -> Math:
        """Display the variables"""
        return Math(self.latex())

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
        return len(self.idx())


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

    def __iter__(self):
        for i in self.vars:
            yield i

    def __call__(self, *key: tuple[Idx] | Idx) -> Self:
        return self.vars[self.idx().index(key)]

    def __getitem__(self, *key: tuple[Idx]):
        if self._fixed:
            return self._[self.idx().index(key)]
