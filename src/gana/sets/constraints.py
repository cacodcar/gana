"""General Constraint Class
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Self

from IPython.display import Math, display
from pyomo.environ import Constraint as PyoCons
from sympy import Rel

from ..elements.constraint import Cons
from .ordered import Set

if TYPE_CHECKING:
    from sympy import Eq, GreaterThan, LessThan

    from ..elements.index import Idx
    from .functions import F
    from .parameters import P
    from .variables import V
    from pyomo.environ import ConcreteModel as PyoModel


class C(Set):
    """Constraint gives the relationship between Parameters, Variables, or Expressions"""

    def __init__(
        self,
        funcs: F,
        leq: bool = False,
    ):
        self.funcs = funcs
        self.leq = leq

        # since indices should match, take any
        order = self.funcs.order

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
                parent=self,
                pos=n,
                func=self.funcs(idx),
                leq=self.leq,
            )
            for n, idx in enumerate(self.idx())
        ]

    def matrix(self):
        """Matrix Representation"""

    def latex(self) -> str:
        """Latex representation"""

        if self.leq:
            rel = r'\leq'

        else:
            rel = r'='

        return rf'{self.funcs.latex()} {rel} 0'

    def pprint(self) -> Math:
        """Display the function"""
        display(Math(self.latex()))

    def sympy(self) -> LessThan | GreaterThan | Eq:
        """sympy representation"""

    #     return Rel(self.funcs.one, self.rhs.sympy(), self.rel)

    def pyomo(self, m: PyoModel) -> PyoCons:

        idx = [i.pyomo() for i in self.order]

        if self.leq:

            def rule(m, *idx):
                return self.funcs.pyomo() <= 0

        else:

            def rule(m, *idx):
                return self.funcs.pyomo() == 0

        return PyoCons(m, *idx, rule=rule, doc=str(self))

    def __call__(self, *key: tuple[Idx] | Idx) -> Cons:
        if len(key) == 1:
            return self._[self.idx().index(key[0])]
        return self._[self.idx().index(key)]

    def __getitem__(self, *key: tuple[Idx] | Idx) -> Cons:
        return self(*key)
