"""Function"""

from __future__ import annotations

from typing import Self, TYPE_CHECKING

from .element import X
from .constraint import Cons


if TYPE_CHECKING:
    from .variable import Var


class Func(X):
    """A function"""

    def __init__(
        self,
        one: float | Var | Self = None,
        rel: str = None,
        two: float | Var | Self = None,
    ):
        self.one = one
        self.rel = rel
        self.two = two

        super().__init__(parent=self.parent, name=self.rel, n=self.n)

    def __neg__(self):

        if self.one:
            one = 0 - self.one
        else:
            one = None

        if self.rel == '+':
            rel = '-'
        elif self.rel == '-':
            rel = '+'
        else:
            rel = self.rel

        two = self.two

        return Func(one=one, rel=rel, two=two)

    def __pos__(self):
        return self

    def __add__(self, other: float | Var | Self):
        return Func(one=self, rel='+', two=other)

    def __radd__(self, other: float | Var | Self):
        if other == 0:
            return self
        else:
            return self + other

    def __sub__(self, other: float | Var | Self):
        return Func(one=self, rel='-', two=other)

    def __rsub__(self, other: float | Var | Self):
        if other == 0:
            return -self
        else:
            return -self + other

    def __mul__(self, other: float | Var | Self):
        return Func(one=self, rel='×', two=other)

    def __truediv__(self, other: float | Var | Self):
        return Func(one=self, rel='÷', two=other)

    def __eq__(self, other: float | Var | Self):
        return Cons(lhs=self, rel='eq', rhs=other)

    def __le__(self, other: float | Var | Self):
        return Cons(lhs=self, rel='le', rhs=other)

    def __ge__(self, other: float | Var | Self):
        return Cons(lhs=self, rel='ge', rhs=other)

    def __lt__(self, other: float | Var | Self):
        return self <= other

    def __gt__(self, other: float | Var | Self):
        return self >= other
