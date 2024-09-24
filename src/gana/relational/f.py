"""Expression 
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

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
        name: str = 'func',
    ):
        self.one = one
        self.two = two
        self.rel = rel
        self.name = name

        if self.one and self.two and self.one.index != self.two.index:
            raise ValueError('Indexes of both variables must be same')

        if self.one:
            self.index = self.one.index
        elif self.two:
            self.index = self.two.index

    @property
    def sym(self) -> Add:
        """symbolic representation"""

        if self.rel == '+':
            if self.one:
                return self.one.sym + self.two.sym
            else:
                return +self.two.sym

        if self.rel == '-':
            if self.one:
                return self.one.sym - self.two.sym
            else:
                return -self.two.sym

        if self.rel == '*':
            return self.one.sym * self.two.sym

        if self.rel == '/':
            return self.one.sym / self.two.sym

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __neg__(self):
        return F(rel='-', two=self)

    def __pos__(self):
        return F(rel='+', two=self)

    def __add__(self, other: Self | P | V):
        return F(one=self, rel='+', two=other)

    def __sub__(self, other: Self | P | V):
        return F(one=self, rel='-', two=other)

    def __mul__(self, other: Self | P | V):
        return F(one=self, rel='*', two=other)

    def __truediv__(self, other: Self | P | V):
        return F(one=self, rel='/', two=other)

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
