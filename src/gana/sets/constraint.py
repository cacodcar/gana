"""General Constraint Class
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self, Literal
from math import prod

from IPython.display import Math, display
from pyomo.environ import Constraint
from sympy import Rel


if TYPE_CHECKING:
    from sympy import Eq, GreaterThan, LessThan

    from .parameter import P
    from .variable import V
    from .function import F
    from .thing import X


class C:
    """Constraint gives the relationship between Parameters, Variables, or Expressions"""

    def __init__(
        self,
        lhs: F | V,
        rhs: P,
        rel: Literal['eq'] | Literal['ge'] | Literal['le'] = 'eq',
        name: str = 'cons',
    ):
        self.lhs = lhs
        self.rhs = rhs
        self.rel = rel
        self.name = name

        # keeps a count of, updated in program
        self.number: int = None
        # since indices should match, take any
        self.index = self.lhs.index

        # whether the constraint is binding
        self.binding = False

        self.parent: Self = None
        self.cons: list[Self] = []

    def canoncial(self, zeros: P) -> Self:
        """Canonical form of the constraint"""
        self.lhs = self.lhs - self.rhs
        if self.rel == 'ge':
            self.lhs = -self.lhs
            self.rel = 'le'
        self.rhs = zeros

    def idx(self) -> list[tuple]:
        """index"""
        if self.parent:
            return self.index
        else:
            return [(i,) if not isinstance(i, tuple) else i for i in prod(self.index)._]

    def __len__(self):
        return len(self.idx())

    def latex(self, descriptive: bool = False) -> str:
        """Latex representation"""
        if self.rel == 'eq':
            rel = r'='

        if self.rel == 'le':
            rel = r'\leq'

        if self.rel == 'ge':
            rel = r'\geq'

        if descriptive:
            return rf'{self.lhs.latex()} {rel} {self.rhs._[0]}'

        return rf'{self.lhs.latex()} {rel} {self.rhs.latex()}'

    def pprint(self, descriptive: bool = False) -> Math:
        """Display the function"""

        if descriptive:
            for c in self.cons:
                display(Math(c.latex(descriptive)))
        else:
            display(Math(self.latex()))

    def sympy(self) -> LessThan | GreaterThan | Eq:
        """sympy representation"""
        return Rel(self.lhs.sympy(), self.rhs.sympy(), self.rel)

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __call__(self, *key: tuple[X] | X) -> Self:
        return self.cons[self.idx().index(key)]
