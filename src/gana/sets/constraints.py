"""General Constraint Class
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from IPython.display import Math, display

from ..elements.constraint import Cons
from .ordered import ESet

if TYPE_CHECKING:
    from ..elements.index import Idx
    from .functions import F
    from .parameters import P
    from .variables import V


class C(ESet):
    """Constraint gives the relationship between Parameters, Variables, or Expressions"""

    def __init__(
        self,
        funcs: F,
        leq: bool = False,
    ):
        self.funcs = funcs
        self.leq = leq

        # since indices should match, take any

        # whether the constraint is binding
        self.binding = False

        self._: list[Cons] = []

        # where this constraint is part of:
        # g - equality constraint
        # h - inequality constraint

        super().__init__()

        self.order = self.funcs.order

    def __setattr__(self, name, value):

        if name == 'n' and isinstance(value, int) and value >= 0:
            self._ = [
                Cons(
                    parent=self,
                    pos=n,
                    func=self.funcs[n],
                    leq=self.leq,
                )
                for n in range(len(self))
            ]

        super().__setattr__(name, value)

    def matrix(self):
        """Matrix Representation"""

    def latex(self) -> str:
        """Latex representation"""

        if self.leq:
            rel = r'\leq'

        else:
            rel = r'='

        return rf'{self.funcs.latex()} {rel} 0'

    def pprint(self, descriptive: bool = False) -> Math:
        """Display the function"""

        if descriptive:
            for c in self._:
                display(Math(c.latex()))
        else:
            display(Math(self.latex()))

    # def rule(self) -> function:
    #     """The rule of the constraint"""
    #     return self.funcs

    def __call__(self, *key: tuple[Idx] | Idx) -> Cons:
        if len(key) == 1:
            return self._[self.idx().index(key[0])]
        return self._[self.idx().index(key)]

    def __getitem__(self, pos: int) -> Cons:
        return self._[pos]
