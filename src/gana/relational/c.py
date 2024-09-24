"""General Constraint Class
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from sympy import Rel


if TYPE_CHECKING:
    from .f import F
    from ..element.p import P
    from ..element.v import V


class C:
    """Constraint gives the relationship between Parameters, Variables, or Expressions"""

    def __init__(self, lhs: F | P | V, rhs: F | P | V, rel: str = 'eq', name: str = 'cons'):
        self.lhs = lhs
        self.rhs = rhs
        self.rel = rel
        self.name = name

        if self.lhs.index != self.rhs.index:
            raise ValueError('Indexes of all variables in a constraint must be same')

    @property
    def sym(self):
        """symbolic representation"""
        return Rel(self.lhs.sym, self.rhs.sym, self.rel)


    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)