"""Function"""

from __future__ import annotations

from typing import Self, TYPE_CHECKING
from IPython.display import Math, display

from .element import X
from .constraint import Cons


if TYPE_CHECKING:
    from .variable import Var
    from ..sets.functions import F


class Func(X):
    """A function"""

    def __init__(
        self,
        parent: list[F] = None,
        name: str = None,
        n: int = None,
        one: float | Var | Self = None,
        rel: str = None,
        two: float | Var | Self = None,
    ):
        self.one = one
        self.rel = rel
        self.two = two

        if not name:
            if self.one:
                name = f'{self.one} {self.rel} {self.two}'
            else:
                name = f'{self.rel} {self.two}'

        super().__init__(parent=parent, name=name, n=n)

    def latex(self) -> str:
        """Equation"""
        if self.one:
            if isinstance(self.one, float):
                one = self.one
            else:
                one = self.one.latex()

        if isinstance(self.two, float):
            two = self.two

        else:
            two = self.two.latex()

        if self.rel == '+':
            if self.one:
                return rf'{one} + {two}'
            else:
                return rf'{two}'

        if self.rel == '-':
            if self.one:
                return rf'{one} - {two}'
            # this is used to generate negatives
            else:
                return rf'-{two}'

        if self.rel == '×':
            return rf'{one} \cdot {two}'

        if self.rel == '÷':
            return rf'\frac{{{one}}}{{{two}}}'

    def pprint(self) -> Math:
        """Display the function"""
        display(Math(self.latex()))

    def __neg__(self):

        if self.one:
            self.one = 0 - self.one
        if self.rel == '+':

            self.rel = '-'

        if self.rel == '-':

            self.rel = '+'

        self.two = self.two

        return self

    def __pos__(self):
        return self

    def __add__(self, other: float | Var | Self):
        self.one = self
        self.rel = '+'
        self.two = other
        return self

    def __radd__(self, other: float | Var | Self):
        if other == 0:
            return self
        else:
            return self + other

    def __sub__(self, other: float | Var | Self):
        self.one = self
        self.rel = '-'
        self.two = other
        return self

    def __rsub__(self, other: float | Var | Self):
        if other == 0:
            return -self
        else:
            return -self + other

    def __mul__(self, other: float | Var | Self):
        self.one = self
        self.rel = '×'
        self.two = other
        return self

    def __truediv__(self, other: float | Var | Self):
        self.one = self
        self.rel = '÷'
        self.two = other
        return self

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
