"""General Constraint Class
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from sympy import Rel


if TYPE_CHECKING:
    from sympy import Eq, GreaterThan, LessThan
    from .f import F
    from ..element.p import P
    from ..element.v import V


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


    def x(self):
        """Elements in the constraint"""
        return sum([f if isinstance(f, list) else [f] for f in self.lhs.x()], [])

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __call__(self) -> LessThan | GreaterThan | Eq:
        """symbolic representation"""
        return Rel(self.lhs(), self.rhs(), self.rel)
