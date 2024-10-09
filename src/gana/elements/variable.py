"""Variable"""

from __future__ import annotations

from typing import Self, TYPE_CHECKING

from .element import X

from .function import Func
from .constraint import Cons

if TYPE_CHECKING:
    from ..sets.variables import V


class Var(X):
    """A variable"""

    def __init__(
        self,
        parent: list[V],
        name: str = None,
        n: int = None,
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

        super().__init__(parent=parent, name=name, n=n)

    def __pos__(self):
        return Func(rel='+', two=self)

    def __neg__(self):
        return Func(rel='-', two=self)

    def __add__(self, other: Self | Func):
        return Func(one=self, rel='+', two=other)

    def __radd__(self, other: Self | Func):
        if other == 0:
            return self
        return self + other

    def __sub__(self, other: Self | Func):
        return Func(one=self, two=other, rel='-')

    def __rsub__(self, other: Self | Func | int):
        if other == 0:
            return -self
        else:
            return -self + other

    def __mul__(self, other: Self | Func):
        return Func(one=self, two=other, rel='×')

    def __rmul__(self, other: Self | Func | int):
        if other == 1:
            return self
        else:
            return self * other

    def __truediv__(self, other: Self | Func):
        return Func(one=self, two=other, rel='÷')

    def __rtruediv__(self, other: Self | Func | int):

        if other == 1:
            return self
        else:
            return self / other

    def __eq__(self, other):
        return Cons(lhs=+self, rhs=other, rel='eq')

    def __le__(self, other):
        return Cons(lhs=+self, rhs=other, rel='le')

    def __ge__(self, other):

        return Cons(lhs=+self, rhs=other, rel='ge')

    def __lt__(self, other):

        return self <= other

    def __gt__(self, other):

        return self >= other
