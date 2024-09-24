"""General Constraint Class
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from sympy import Rel


if TYPE_CHECKING:
    from .f import F
    from ..element.p import P
    from ..element.v import V


@dataclass
class C:
    """Constraint gives the relationship between Parameters, Variables, or Expressions"""

    lhs: F | P | V = field()
    rhs: F | P | V = field()
    rel: str = field(default='eq')
    name: str = field(default='Cns')

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)