"""Constraint"""

from __future__ import annotations

from typing import Literal, TYPE_CHECKING
from IPython.display import Math, display

from .element import X

if TYPE_CHECKING:
    from .variable import Var
    from .function import Func
    from ..sets.constraints import C


class Cons(X):
    """A constraint"""

    def __init__(
        self,
        pos: int,
        parent: C,
        rhs: Func | Var | float,
        lhs: Func | Var | float,
        rel: Literal['eq'] | Literal['ge'] | Literal['le'] = 'eq',
    ):
        self.lhs = lhs
        self.rhs = rhs
        self.rel = rel

        super().__init__(parent, pos)

    def latex(self) -> str:
        """Latex representation"""

        if isinstance(self.rhs, float):
            rhs = self.rhs

        else:
            rhs = self.rhs.latex()

        if isinstance(self.lhs, float):
            lhs = self.lhs

        else:
            lhs = self.lhs.latex()

        if self.rel == 'eq':
            rel = r'='

        if self.rel == 'le':
            rel = r'\leq'

        if self.rel == 'ge':
            rel = r'\geq'

        return rf'{lhs} {rel} {rhs}'

    def pprint(self):
        """Pretty Print"""
        display(Math(self.latex()))
