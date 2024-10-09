"""Constraint"""

from __future__ import annotations

from typing import Literal, TYPE_CHECKING

from .element import X

if TYPE_CHECKING:
    from .variable import Var
    from .function import Func


class Cons(X):
    """A constraint"""

    def __init__(
        self,
        lhs: Func | Var | float,
        rhs: Func | Var | float,
        rel: Literal['eq'] | Literal['ge'] | Literal['le'] = 'eq',
    ):
        self.lhs = lhs
        self.rhs = rhs
        self.rel = rel

        super().__init__(parent=self.parent, name=self.name, n=self.n)
