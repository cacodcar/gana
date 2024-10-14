"""Mathematical Program"""

from dataclasses import dataclass, field
from itertools import product

# from typing import Self
from warnings import warn

from IPython.display import display

from ..elements.constraint import Cons
from ..elements.function import Func

# from ..sets.objective import O
from ..elements.index import Idx
from ..elements.variable import Var

from ..sets.constraints import C
from ..sets.functions import F
from ..sets.parameters import P
from ..sets.indices import I

# from ..value.zero import Z
from ..sets.ordered import Set

# from ..sets.theta import T
from ..sets.variables import V


from pyomo.environ import ConcreteModel


@dataclass
class Prg:
    """A mathematical program"""

    name: str = field(default=':p:')
    tol: float = field(default=None)
    canonical: bool = field(default=True)

    def __post_init__(self):
        # names of declared modeling and relational elements
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
            self.idxsets.append(value)
            value.n = len(self.idxsets)

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
            self.indices.append(value)
            value.n = len(self.indices)
            self.names_idx.append(value.name)

        if isinstance(value, P):
            self.parsets.append(value)
            value.n = len(self.parsets)

        if isinstance(value, V):
            self.varsets.append(value)
            value.n = len(self.varsets)

            for n, var in enumerate(value._):
                setattr(self, var.name, var)

        if isinstance(value, Var):
            self.variables.append(value)
            value.n = len(self.variables)

            if value.bnr:
                self.vars_bnr.append(value)

            if value.nn:
                self.vars_nn.append(value)

            if value.itg:
                self.vars_itg.append(value)

            else:
                self.vars_cnt.append(value)

        if isinstance(value, F):
            self.funcsets.append(value)
            value.n = len(self.funcsets)

            for n, fun in enumerate(value._):
                setattr(self, fun.name, fun)

        if isinstance(value, Func):
            self.functions.append(value)
            value.n = len(self.functions)

        if isinstance(value, C):
            # value.canoncial()
            self.conssets.append(value)
            value.n = len(self.conssets)

            for n, con in enumerate(value._):
                setattr(self, con.name, con)

        if isinstance(value, Cons):
            self.constraints.append(value)
            value.n = len(self.constraints)
            if not value.name:
                value.name = name

        super().__setattr__(name, value)

    # def combine(self, *prgs: tuple[Self]):
    #     """Club Programs"""
    #     for prg in prgs:
    #         if isinstance(prg, Prg):
    #             # modeling elements
    #             self.indices = self.indices + prg.indices
    #             self.variables = self.variables + prg.variables
    #             self.vars_cnt = self.vars_cnt + prg.vars_cnt
    #             self.vars_itg = self.vars_itg + prg.vars_itg
    #             self.vars_nn = self.vars_nn + prg.vars_nn
    #             self.vars_bnr = self.vars_bnr + prg.vars_bnr
    #             self.thetas = self.thetas + prg.thetas
    #             self.parameters = self.parameters + prg.parameters
    #             self.functions = self.functions + prg.functions
    #             self.constraints = self.constraints + prg.constraints
    #             self.objectives = self.objectives + prg.objectives

    def matrix(self):
        """Return Matrix Representation"""

    @property
    def order(self):
        """Set of all indices"""
        return I(product(*[s._ if isinstance(s, I) else [s] for s in self.indices]))

    @property
    def dim(self):
        """Dimension of the program"""
        return len(self.indices)

    def pyomo(self):
        """Return Pyomo Model"""

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
        """Return MPS File"""

    def lp(self):
        """Return LP File"""

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

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))
