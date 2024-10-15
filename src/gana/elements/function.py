"""Function"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from IPython.display import Math, display

from .constraint import Cons
from .element import X

if TYPE_CHECKING:
    from ..sets.functions import F
    from .variable import Var


class Func(X):
    """A function"""

    def __init__(
        self,
        parent: F | Cons | Var = None,
        pos: int = None,
        one: float | Var | Self = None,
        rel: str = None,
        two: float | Var | Self = None,
    ):

        self.one = one
        self.rel = rel
        self.two = two
        # the relation between one and two
        # presented as a dictionary
        self._ = [self.one, self.two]

        super().__init__(parent=parent, pos=pos)

        self.a = []  # variable vector
        self.b = 0  # parameter added or subtracted goes in the parameter vector

        if self.one and isinstance(self.one, (int, float)):
            if self.rel in ['+', '-']:
                self.b = float(self.one)
                
            if self.rel in ['×']:
                self.a.append(float(self.one))
            self.basic = True


        if self.two and isinstance(self.two, (int, float)):
            if self.rel in ['+', '-']:
                self.b = float(self.two)

            if isinstance(self.one, Func):

                self.a += self.one.a
                self.b += self.one.b

            one = rf'{self.one}'
        else:
            one = ''

        if self.two:

            two = rf'{self.two}'

            if isinstance(self.two, (int, float)):
                if self.rel in ['+', '-']:
                    self.b = self.two
                if self.rel in ['×']:
                    self.a.append(float(self.two))
                self.basic = True

            if isinstance(self.two, Func):
                self.a += self.two.a
                self.b += self.two.b

        else:
            two = ''

        self.name = f'{one} {self.rel} {two}'

    # def x(self):

    #     for i in self._:
    #         if isinstance(i, Func):
    #             self.a += i.a
    #             self.b += i.b
    #         elif isinstance(i, (int, float)):
    #             self.b += i
    #         else:
    #             if self.rel = '+':
    #                 self.a.append(1)

    def latex(self) -> str:
        """Equation"""
        if self.one:
            if isinstance(self.one, (int, float)):
                one = self.one
            else:
                one = self.one.latex()
        else:
            one = ''

        if self.two:
            if isinstance(self.two, (int, float)):
                two = self.two

            else:
                two = self.two.latex()
        else:
            two = ''

        if self.rel == '+':
            return rf'{one} + {two}'

        if self.rel == '-':
            return rf'{one} - {two}'

        if self.rel == '×':
            return rf'{one} \cdot {two}'

        if self.rel == '÷':
            return rf'\frac{{{one}}}{{{two}}}'

    def matrix(self) -> list:
        """Variables in the function"""

    def pprint(self) -> Math:
        """Display the function"""
        display(Math(self.latex()))

    def __neg__(self):

        if self.one:
            one = self.one.__neg__()
        else:
            one = None

        if self.two:
            two = self.two

        else:
            two = None

        if self.rel == '+':

            rel = '-'

        elif self.rel == '-':

            rel = '+'
        else:
            rel = self.rel

        return Func(one=one, rel=rel, two=two)

    def __pos__(self):
        return self

    def __add__(self, other: float | Var | Self):
        # the number element is always taken at number two
        if isinstance(self.two, float):
            if isinstance(other, (int, float)):
                one = self.one
                two = self.two + float(other)
                if two < 0:
                    rel = '-'
                    two = -two
                else:
                    rel = '+'
            else:
                two = self.two
                one = self.one + other
                rel = '+'

            return Func(one=one, rel=rel, two=two)

        if isinstance(self.one, float):
            if isinstance(other, (int, float)):
                one = self.one + float(other)
                two = self.two
            else:
                one = self.one
                two = self.two + other

            return Func(one=one, rel='+', two=two)

        return Func(one=self, rel='+', two=other)

    def __radd__(self, other: float | Var | Self):
        if other == 0:
            return self
        else:
            return self + other

    def __sub__(self, other: float | Var | Self):

        if isinstance(self.two, float):
            if isinstance(other, (int, float)):
                one = self.one
                two = self.two - float(other)
                if two < 0:
                    rel = '-'
                    two = -two
                else:
                    rel = '+'
            else:
                one = self.one - other
                two = self.two
                rel = '-'

            return Func(one=one, rel=rel, two=two)

        if isinstance(self.one, float):
            if isinstance(other, (int, float)):
                one = self.one - float(other)
                two = self.two
            else:
                one = self.one
                two = self.two - other

            return Func(one=one, rel='-', two=two)

        return Func(one=self, rel='-', two=other)

    def __rsub__(self, other: float | Var | Self):
        if other == 0:
            return -self
        else:
            return -self + other

    def __mul__(self, other: float | Var | Self):
        return Func(one=self, two=other, rel='×')

    def __truediv__(self, other: float | Var | Self):
        return Func(one=self, two=other, rel='÷')

    def __eq__(self, other: float | Var | Self):
        return Cons(func=self - other)

    def __le__(self, other: float | Var | Self):
        return Cons(func=self - other, leq=True)

    def __ge__(self, other: float | Var | Self):
        return Cons(func=-self + other, leq=True)

    def __lt__(self, other: float | Var | Self):
        return self <= other

    def __gt__(self, other: float | Var | Self):
        return self >= other
