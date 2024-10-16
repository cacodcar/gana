"""Mathematical Program"""

from dataclasses import dataclass, field
from typing import Self

from IPython.display import display
from pyomo.environ import ConcreteModel

from ..elements.constraint import Cons
from ..elements.element import X
from ..elements.function import Func

# from ..sets.objective import O
from ..elements.index import Idx
from ..elements.variable import Var
from ..sets.constraints import C
from ..sets.functions import F
from ..sets.indices import I

# from ..value.zero import Z
from ..sets.ordered import Set
from ..sets.parameters import P

# from ..sets.theta import T
from ..sets.variables import V


@dataclass
class Prg:
    """A mathematical program"""

    name: str = field(default=':p:')
    tol: float = field(default=None)
    canonical: bool = field(default=True)

    def __post_init__(self):
        # names of declared modeling and relational elements
        self.restricted_names = ['a', 'b']
        self.names = []
        self.names_idx = []
        self.idxsets: list[I] = []
        self.indices: list[Idx] = []
        self.varsets: list[V] = []
        self.variables: list[Var] = []
        self.vars_cnt: list[V] = []
        self.vars_itg: list[V] = []
        self.vars_nn: list[V] = []
        self.vars_bnr: list[V] = []
        self.parsets: list[P] = []
        # self.thetas: list[T] = []
        self.funcsets: list[F] = []
        self.functions: list[Func] = []
        self.conssets: list[C] = []
        self.constraints: list[Cons] = []
        # self.cons_eq: list[C] = []
        # self.cons_leq: list[C] = []
        # self.objectives: list[O] = []

    def __setattr__(self, name, value) -> None:

        if isinstance(value, (Set, X)) and name in self.restricted_names:
            raise ValueError(f'Cannot use {name} as a name')

        # Collect names here
        # indices can belong to multiple sets
        # Hence they can be overwritten
        if isinstance(value, Set):

            if name[-1] == '_':
                raise ValueError(
                    'Ending name with underscore is not recommended, can cause printing issues'
                )

            if name in self.names:
                raise ValueError(f'Overwriting {name}')

            value.name = name
            self.names.append(name)
            value.process()

        if isinstance(value, I):
            value.n = len(self.idxsets)
            self.idxsets.append(value)

            for n, idx in enumerate(value._):
                if idx.name in self.names_idx:
                    # if index already declared as part of another index set
                    # update her parent

                    idx = self.indices[self.indices.index(idx)]
                    idx.parent.append(value)
                    idx.pos.append(n)
                    value._[n] = idx
                else:
                    setattr(self, idx.name, idx)

        if isinstance(value, Idx):
            value.n = len(self.indices)
            self.indices.append(value)
            self.names_idx.append(value.name)

        if isinstance(value, P):
            value.n = len(self.parsets)
            self.parsets.append(value)

        if isinstance(value, V):
            value.n = len(self.varsets)
            self.varsets.append(value)

            for n, var in enumerate(value._):
                setattr(self, var.name, var)

        if isinstance(value, Var):
            value.n = len(self.variables)
            self.variables.append(value)

            if value.bnr:
                self.vars_bnr.append(value)

            if value.nn:
                self.vars_nn.append(value)

            if value.itg:
                self.vars_itg.append(value)

            else:
                self.vars_cnt.append(value)

        if isinstance(value, F):
            value.n = len(self.funcsets)
            self.funcsets.append(value)

            for fun in value._:
                setattr(self, fun.name, fun)

        if isinstance(value, Func):
            value.n = len(self.functions)
            self.functions.append(value)

        if isinstance(value, C):
            # value.canoncial()
            value.n = len(self.conssets)
            self.conssets.append(value)

            for con in value._:
                setattr(self, con.name, con)

        if isinstance(value, Cons):
            value.n = len(self.constraints)
            print(value.n)
            self.constraints.append(value)
            if not value.name:
                value.name = name

        super().__setattr__(name, value)

    def b(self, zero: bool = False) -> list[float | None]:
        """RHS Parameter vector"""
        return [c.func.b(zero) for c in self.constraints]

    def a(self, zero: bool = False) -> list[float | None]:
        """Matrix of Variable coefficients"""
        a_ = []

        for c in self.constraints:
            if zero:
                row = [0] * len(self.variables)

            else:
                row = [None] * len(self.variables)
            for n, value in zip(c.x(), c.a()):
                row[n] = value
            a_.append(row)

        return a_

    def g(self, zero: bool = False) -> list[float | None]:
        """Matrix of Variable coefficients for type:

        g < = 0
        """

    def h(self, zero: bool = False) -> list[float | None]:
        """Matrix of Variable coefficients for type:

        h = 0
        """

    def pyomo(self):
        """Pyomo Model"""

        m = ConcreteModel()

        for s in self.idxsets:
            setattr(m, s.name, s.pyomo())

        for v in self.varsets:
            setattr(m, v.name, v.pyomo())

        # for p in self.parsets:
        #     setattr(m, p.name, p.pyomo())

        # for c in self.conssets:
        #     setattr(m, c.name, c.pyomo(m))

        return m

    def mps(self):
        """MPS File"""

    def lp(self):
        """LP File"""

    def latex(self, descriptive: bool = False):
        """Display LaTeX"""

        for s in self.idxsets:
            display(s.latex())

        if descriptive:
            for c in self.constraints:
                display(c.latex())

        else:
            for c in self.conssets:  # + self.objectives:
                display(c.latex())

    def pprint(self, descriptive: bool = False):
        """Pretty Print"""

        for i in self.idxsets:
            i.pprint(True)

        if descriptive:
            for c in self.constraints:
                c.pprint()

        else:
            for c in self.conssets:  # + self.objectives:
                c.pprint()

            for c in self.constraints:
                if not c.parent:
                    c.pprint()

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __add__(self, other: Self):
        """Add two programs"""

        if not isinstance(other, Prg):
            raise ValueError('Can only add programs')

        prg = Prg(name=rf'{self.name}_{other.name}')

        for i in (
            self.idxsets
            + self.varsets
            + self.parsets
            + self.funcsets
            + self.conssets
            + other.idxsets
            + other.varsets
            + other.parsets
            + other.funcsets
            + other.conssets
        ):
            setattr(prg, i.name, i)

        for c in self.constraints + other.constraints:
            if c not in prg.constraints:
                setattr(prg, c.name, c)

        return prg
