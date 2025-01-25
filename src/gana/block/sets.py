"""Block of Sets"""

from dataclasses import dataclass

from ..sets.constraint import C
from ..sets.function import F
from ..sets.index import I
from ..sets.parameter import P
from ..sets.theta import T
from ..sets.variable import V


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

        self._cons_names: list[str] = []
        self._idx_names: list[str] = []

        # number of:
        self._ni = 0  # index sets
        self._nv = 0  # variable sets
        self._np = 0  # parameter sets
        self._nt = 0  # theta sets
        self._nf = 0  # function sets
        self._nc = 0  # constraint sets

    @property
    def I_nn(self) -> I:
        """non-negative variable set"""
        i = I(*[str(v) for v in self.nnvars()])
        i.name = 'nnvars'
        return i

    def __setattr__(self, name, value):

        if isinstance(value, (int, list)):
            super().__setattr__(name, value)
            return

        elif isinstance(value, I):
            value.name = name
            if not name in self._idx_names:
                self.index.append(value)
                self._idx_names.append(name)
                value.n = self._ni
                self._ni += 1

            else:
                self.index[self.index.index(getattr(self, name))] = value
                value.n = getattr(self, name).n

            super().__setattr__(name, value)
            return

        elif isinstance(value, V):
            value.name = name
            value.n = self._nv
            self._nv += 1
            self.variable.append(value)
            super().__setattr__(name, value)
            return

        elif isinstance(value, P):
            if not value.name:
                value.name = name
            value.n = self._np
            self._np += 1
            self.parameter.append(value)
            super().__setattr__(name, value)
            return

        elif isinstance(value, T):
            value.name = name
            value.n = self._nt
            self._nt += 1
            self.theta.append(value)
            super().__setattr__(name, value)
            return

        elif isinstance(value, F):
            value.n = self._nf
            self._nf += 1
            self.function.append(value)
            super().__setattr__(name, value)
            return

        elif isinstance(value, C):
            value.n = self._nc
            self._nc += 1
            if not name in self._cons_names:
                self.constraint.append(value)
                self._cons_names.append(name)

            super().__setattr__(name, value)
            return

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
