"""Expression 
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self
from math import prod

from IPython.display import Math

from .constraints import C
from .ordered import Set


if TYPE_CHECKING:
    from sympy import Add

    from .parameters import P
    from .variables import V
    from ..elements.element import X


class F(Set):
    """Provides some relational operation between Parameters and Variables"""

    def __init__(
        self,
        one: P | V | Self = None,
        rel: str = '+',
        two: P | V | Self = None,
    ):
        self.one: P | V | Self = one
        self.two = two
        self.rel = rel

        if self.one and len(self.one) != len(self.two):
            raise ValueError(
                'Cannot operate with variable sets with different cardinalities'
            )

        if self.one:
            self.index = self.one.index
        elif self.two:
            self.index = self.two.index

        # keeps a count of, updated in program
        self.number: int = None

        if self.one:
            self.name = f'{self.one}{self.rel}{self.two}'
        else:
            self.name = f'{self.rel}{self.two}'

        self.parent: Self = None
        self.funs: list[Self] = []

        # the flag _fixed is changed when .fix(val) is called
        self._fixed = False

    @property
    def _(self):
        """Elements in the function"""
        return sum(
            [i._ if isinstance(i, F) else F(i) for i in [self.one, self.two] if i], []
        )

    def matrix(self):
        """Variables in the function"""

        return sum(
            [
                i.matrix() if isinstance(i, F) else [i.number]
                for i in [self.one, self.two]
                if i
            ],
            [],
        )

    def latex(self) -> str:
        """Equation"""
        if self.rel == '+':
            if self.one:
                return rf'{self.one.latex()} + {self.two.latex()}'
            else:
                return rf'{self.two.latex()}'

        if self.rel == '-':
            if self.one:
                return rf'{self.one.latex()} - {self.two.latex()}'
            # this is used to generate negatives
            else:
                return rf'-{self.two.latex()}'

        if self.rel == '×':
            return rf'{self.one.latex()} \cdot {self.two.latex()}'

        if self.rel == '÷':
            return rf'\frac{{{self.one.latex()}}}{{{self.two.latex()}}}'

    def pprint(self) -> Math:
        """Display the function"""
        return Math(self.latex())

    def sympy(self) -> Add:
        """Equation"""
        if self.rel == '+':
            if self.one:
                return self.one.sympy() + self.two.sympy()
            else:
                return self.two.sympy()

        if self.rel == '-':
            if self.one:
                return self.one.sympy() - self.two.sympy()
            # this is used to generate negatives
            else:
                return -self.two.sympy()

        if self.rel == '×':
            return self.one.sympy() * self.two.sympy()

        if self.rel == '÷':
            return self.one.sympy() / self.two.sympy()

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

        return F(one=one, rel=rel, two=two)

    def __pos__(self):
        return self

    def __add__(self, other: Self | P | V):
        return F(one=self, rel='+', two=other)

    def __radd__(self, other: Self | P | V | int):
        if other == 0:
            return self
        else:
            return self + other

    def __sub__(self, other: Self | P | V):
        return F(one=self, rel='-', two=other)

    def __rsub__(self, other: Self | P | V):
        if other == 0:
            return -self
        else:
            return -self + other

    def __mul__(self, other: Self | P | V):
        return F(one=self, rel='×', two=other)

    def __truediv__(self, other: Self | P | V):
        return F(one=self, rel='÷', two=other)

    def __eq__(self, other: Self | P | V):
        return C(lhs=self, rel='eq', rhs=other)

    def __le__(self, other: Self | P | V):
        return C(lhs=self, rel='le', rhs=other)

    def __ge__(self, other: Self | P | V):
        return C(lhs=self, rel='ge', rhs=other)

    def __lt__(self, other: Self | P | V):
        return self <= other

    def __gt__(self, other: Self | P | V):
        return self >= other

    def __call__(self, *key: tuple[X] | X) -> Self:
        if self.funs:
            return self.funs[self.idx().index(key)]
        else:
            if self.one:
                f = F(one=self.one(*key), rel=self.rel, two=self.two(*key))
            else:
                f = F(rel=self.rel, two=self.two(*key))
            f.parent = self
            return f

    def __getitem__(self, *key: tuple[X]):
        if self._fixed:
            return self._[self.idx().index(key)]
