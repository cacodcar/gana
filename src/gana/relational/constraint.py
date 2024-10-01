"""General Constraint Class
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from IPython.display import Math
from pyomo.environ import Constraint
from sympy import Rel

if TYPE_CHECKING:
    from sympy import Eq, GreaterThan, LessThan

    from ..sets.parameter import P
    from ..sets.variable import V
    from .function import F


class C:
    """Constraint gives the relationship between Parameters, Variables, or Expressions"""

    def __init__(self, lhs: F | V, rhs: P, rel: str = 'eq', name: str = 'cons'):
        self.lhs = lhs
        self.rhs = rhs
        self.rel = rel
        self.name = name

        # keeps a count of, updated in program
        self.count: int = None
        # since indices should match, take any
        self.index = self.lhs.index

        # whether the constraint is binding
        self.binding = False

    def x(self):
        """Elements in the constraint"""
        return sum([f if isinstance(f, list) else [f] for f in self.lhs.x()], [])

    def latex(self):
        """Latex representation"""
        if self.rel == 'eq':
            rel = r'='

        if self.rel == 'le':
            rel = r'\leq'

        if self.rel == 'ge':
            rel = r'\geq'

        return rf'{self.lhs.latex()} {rel} {self.rhs.latex()}'

    def sympy(self) -> LessThan | GreaterThan | Eq:
        """sympy representation"""
        return Rel(self.lhs.sympy(), self.rhs.sympy(), self.rel)

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __call__(self) -> LessThan | GreaterThan | Eq:
        """symbolic representation"""
        return Math(self.latex())
