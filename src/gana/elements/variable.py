"""Variable"""

from __future__ import annotations

from typing import Self, TYPE_CHECKING
from IPython.display import Math, display

from .element import X

from .function import Func
from .constraint import Cons

if TYPE_CHECKING:
    from ..sets.variables import V


class Var(X):
    """A variable"""

    def __init__(
        self,
        parent: V,
        pos: int,
        itg: bool = False,
        nn: bool = True,
        bnr: bool = False,
    ):

        # if the variable is an integer variable
        self.itg = itg
        # if the variable is binary
        self.bnr = bnr
        # if the variable is non negative
        self.nn = nn
        super().__init__(parent=parent, pos=pos)

    def latex(self):
        """Latex representation"""
        return (
            rf'{self.parent.name}'
            + r'_{'
            + rf'{self.parent.idx()[self.pos]}'.replace('(', '').replace(')', '')
            + r'}'
        )

    def pprint(self):
        """Pretty Print"""
        display(Math(self.latex()))

    def __pos__(self):
        return Func(one=self, rel='+')

    def __neg__(self):
        return Func(rel='-', two=self)

    def __add__(self, other: Self | Func):
        if other == 0:
            return self
        return Func(one=self, rel='+', two=other)

    def __radd__(self, other: Self | Func):
        if isinstance(other, (int, float)):
            if other == 0:
                return self
            other = float(other)
        return self + other

    def __sub__(self, other: Self | Func):
        if other == 0:
            return self
        return Func(one=self, rel='-', two=other)

    def __rsub__(self, other: Self | Func | int):

        if isinstance(other, (int, float)):
            if other == 0:
                return -self
            other = float(other)
        return -self + other

    def __mul__(self, other: Self | Func):
        return Func(one=self, two=other, rel='×')

    def __rmul__(self, other: Self | Func | int):
        if other == 1:
            return self
        else:
            return Func(one=other, two=self, rel='×')

    def __truediv__(self, other: Self | Func):
        return Func(one=self, two=other, rel='÷')

    def __rtruediv__(self, other: Self | Func | int):

        if other == 1:
            return self
        else:
            return Func(one=other, two=self, rel='÷')

    def __eq__(self, other):
        return Cons(func=self - other)

    def __le__(self, other):
        return Cons(func=self - other, leq=True)

    def __ge__(self, other):

        return Cons(func=other - self, leq=True)

    def __lt__(self, other):

        return self <= other

    def __gt__(self, other):

        return self >= other
