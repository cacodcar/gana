"""General Constraint Class
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self, Literal

from IPython.display import Math, display
from pyomo.environ import Constraint
from sympy import Rel

from .ordered import Set
from ..elements.constraint import Cons

if TYPE_CHECKING:
    from sympy import Eq, GreaterThan, LessThan

    from .parameters import P
    from .variables import V
    from .functions import F
    from ..elements.index import Idx


class C(Set):
    """Constraint gives the relationship between Parameters, Variables, or Expressions"""

    def __init__(
        self,
        lhs: F | V,
        rhs: P,
        rel: Literal['eq'] | Literal['ge'] | Literal['le'] = 'eq',
    ):
        self.lhs = lhs
        self.rhs = rhs
        self.rel = rel

        # since indices should match, take any
        order = self.lhs.order

        # whether the constraint is binding
        self.binding = False

        self._: list[Cons] = []

        # where this constraint is part of:
        # g - equality constraint
        # h - inequality constraint

        super().__init__(*order)

    def process(self):
        """Process the constraint"""
        self._ = [
            Cons(
                name=f'{self.name}_{n}',
                parent=self,
                n=n,
                lhs=self.lhs(idx),
                rel=self.rel,
                rhs=self.rhs(idx),
            )
            for n, idx in enumerate(self.idx())
        ]

    def canoncial(self, zeros: P) -> Self:
        """Canonical form of the constraint"""
        self.lhs = self.lhs - self.rhs
        if self.rel == 'ge':
            self.lhs = -self.lhs
            self.rel = 'le'
        self.rhs = zeros

    def matrix(self):
        """Matrix Representation"""

    def latex(self) -> str:
        """Latex representation"""
        if self.rel == 'eq':
            rel = r'='

        if self.rel == 'le':
            rel = r'\leq'

        if self.rel == 'ge':
            rel = r'\geq'

        return rf'{self.lhs.latex()} {rel} {self.rhs.latex()}'

    def pprint(self) -> Math:
        """Display the function"""
        display(Math(self.latex()))

    def sympy(self) -> LessThan | GreaterThan | Eq:
        """sympy representation"""
        return Rel(self.lhs.sympy(), self.rhs.sympy(), self.rel)

    def __call__(self, *key: tuple[Idx] | Idx) -> Cons:
        if len(key) == 1:
            return self._[self.idx().index(key[0])]
        return self._[self.idx().index(key)]

    def __getitem__(self, *key: tuple[Idx] | Idx) -> Cons:
        return self(*key)
