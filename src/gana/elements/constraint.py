"""Constraint"""

from __future__ import annotations

from typing import Literal, TYPE_CHECKING

from .element import X

if TYPE_CHECKING:
    from .variable import Var
    from .function import Func
    from ..sets.constraints import C


class Cons(X):
    """A constraint"""

    def __init__(
        self,
        rhs: Func | Var | float,
        lhs: Func | Var | float,
        parent: list[C] = None,
        name: str = None,
        n: int = None,
        rel: Literal['eq'] | Literal['ge'] | Literal['le'] = 'eq',
    ):
        self.lhs = lhs
        self.rhs = rhs
        self.rel = rel

        if not name:
            name = f'{self.lhs} {self.rel} {self.rhs}'

        super().__init__(parent=parent, name=name, n=n)
