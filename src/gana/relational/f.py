"""Expression 
"""

from __future__ import annotations

from operator import is_not
from typing import TYPE_CHECKING, Self

from IPython.display import Math

from .c import C

if TYPE_CHECKING:
    from sympy import Add

    from ..element.p import P
    from ..element.v import V


class F:
    """Provides some relational operation between Parameters and Variables

    Attributes:
        P1 (Parameter): First Parameter
        component (IsDfn): Component for which variable is being defined
        symbol (IndexedBase): Symbolic representation of the Variable
    """

    def __init__(
        self,
        one: P | V | Self = None,
        rel: str = '+',
        two: P | V | Self = None,
    ):
        self.one = one
        self.two = two
        self.rel = rel

        if (
            self.one
            and self.two
            and not isinstance(self.two, F)
            and not isinstance(self.one, F)
            and is_not(self.one.mum, self.two.mum)
            and self.one.index != self.two.index
        ):
            raise ValueError('Cant operate with variables of different indices')

        if self.one:
            self.index = self.one.index
        elif self.two:
            self.index = self.two.index

        # keeps a count of, updated in program
        self.count: int = None
        self.name = f'{self.one}{self.rel}{self.two}'

    def x(self):
        """Elements in the function"""
        return sum(
            [i.x() if isinstance(i, F) else [i] for i in [self.one, self.two] if i], []
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

    def __add__(self, other: Self | P | V):
        return F(one=self, rel='+', two=other)

    def __radd__(self, other: Self | P | V | int):
        if other == 0:
            return self
        else:
            return self + other

    def __sub__(self, other: Self | P | V):
        return F(one=self, rel='-', two=other)

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

    def __call__(self) -> str:
        """symbolic representation"""
        return Math(self.latex())
