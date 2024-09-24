"""Expression 
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from .c import C

if TYPE_CHECKING:
    from ..element.p import P
    from ..element.v import V


class F:
    """Provides some relational operation between Parameters and Variables

    Attributes:
        P1 (Parameter): First Parameter
        component (IsDfn): Component for which variable is being defined
        symbol (IndexedBase): Symbolic representation of the Variable
    """

    def __init__(self, one: P | V | Self, two: P | V | Self, rel: str, name: str = 'func'):
        self.one = one
        self.two = two
        self.rel = rel
        self.name = name
        
        if self.one.index != self.two.index:
            raise ValueError('Indexes of both variables must be same')

        # since indices should match, take any
        self.index = self.one.index

    @property
    def sym(self):
        """symbolic representation"""
        if self.rel == '+':
            return self.one.sym + self.two.sym

        if self.rel == '-':
            return self.one.sym - self.two.sym

        if self.rel == '*':
            return self.one.sym * self.two.sym

        if self.rel == '/':
            return self.one.sym / self.two.sym

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __add__(self, other: Self | P | V):
        return F(one=self, two=other, rel='+')

    def __sub__(self, other: Self | P | V):
        return F(one=self, two=other, rel='-')

    def __mul__(self, other: Self | P | V):
        return F(one=self, two=other, rel='*')

    def __truediv__(self, other: Self | P | V):
        return F(one=self, two=other, rel='/')

    def __eq__(self, other: Self | P | V):
        return C(lhs=self, rhs=other, rel='eq')

    def __le__(self, other: Self | P | V):
        return C(lhs=self, rhs=other, rel='le')

    def __ge__(self, other: Self | P | V):
        return C(lhs=self, rhs=other, rel='ge')

    def __lt__(self, other: Self | P | V):
        return self <= other

    def __gt__(self, other: Self | P | V):
        return self >= other
