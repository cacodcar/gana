"""Block of Sets"""

from dataclasses import dataclass
from ..sets.index import I
from ..sets.variable import V
from ..sets.parameter import P
from ..sets.theta import T
from ..sets.function import F
from ..sets.constraint import C


@dataclass
class Sets:
    """Collects and processes Program Set objects"""

    def __post_init__(self):
        self.index: list[I] = []
        self.variable: list[V] = []
        self.parameter: list[P] = []
        self.theta: list[T] = []
        self.function: list[F] = []
        self.constraint: list[C] = []

    def __setattr__(self, name, value):

        if isinstance(value, I):
            value.name = name
            value.n = len(self.index)
            self.index.append(value)

        if isinstance(value, V):
            value.name = name
            value.n = len(self.variable)
            self.variable.append(value)

        if isinstance(value, P):
            value.name = name
            value.n = len(self.parameter)
            self.parameter.append(value)

        if isinstance(value, F):
            value.n = len(self.function)
            self.function.append(value)

        if isinstance(value, C):
            value.n = len(self.constraint)
            self.constraint.append(value)

        super().__setattr__(name, value)

    def nncons(self, n: bool = False) -> list[int | C]:
        """non-negativity constraints"""
        if n:
            return [x.n for x in self.constraint if x.nn]
        return [x for x in self.constraint if x.nn]

    def eqcons(self, n: bool = False) -> list[int | C]:
        """equality constraints"""
        if n:
            return [x.n for x in self.constraint if not x.leq]
        return [x for x in self.constraint if not x.leq]

    def leqcons(self, n: bool = False) -> list[int | C]:
        """less than or equal constraints"""
        if n:
            return [x.n for x in self.constraint if x.leq and not x.nn]
        return [x for x in self.constraint if x.leq and not x.nn]

    def cons(self, n: bool = False) -> list[int | C]:
        """constraints"""
        return self.leqcons(n) + self.eqcons(n) + self.nncons(n)

    def nnvars(self, n: bool = False) -> list[int | V]:
        """non-negative variables"""
        if n:
            return [x.n for x in self.variable if x.nn]
        return [x for x in self.variable if x.nn]

    def bnrvars(self, n: bool = False) -> list[int | V]:
        """binary variables"""
        if n:
            return [x.n for x in self.variable if x.bnr]
        return [x for x in self.variable if x.bnr]

    def intvars(self, n: bool = False) -> list[int | V]:
        """integer variables"""
        if n:
            return [x.n for x in self.variable if x.itg]
        return [x for x in self.variable if x.itg]

    def contvars(self, n: bool = False) -> list[int | V]:
        """continuous variables"""
        if n:
            return [x.n for x in self.variable if not x.bnr and not x.itg]
        return [x for x in self.variable if not x.bnr and not x.itg]
