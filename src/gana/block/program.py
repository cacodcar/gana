"""Mathematical Program"""

from dataclasses import dataclass, field
from itertools import product

# from typing import Self
from warnings import warn

from IPython.display import display

# from ..sets.parameter import P
from ..sets.indices import I

# from ..sets.theta import T
from ..sets.variables import V
from ..sets.functions import F
from ..sets.constraints import C

# from ..sets.objective import O
from ..elements.index import Idx
from ..elements.variable import Var
from ..elements.function import Func
from ..elements.constraint import Cons

# from ..value.zero import Z
from ..sets.ordered import Set


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
        # self.parameters: list[P] = []
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
                    idx = self.indices[self.indices.index(idx)]
                    idx.parent.append(value)
                    value._[n] = idx
                else:
                    setattr(self, idx.name, idx)

        if isinstance(value, Idx):
            self.indices.append(value)
            value.n = len(self.indices)
            self.names_idx.append(value.name)

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

        #         # if only a single integer is passed
        #         # create an orderd set of that length
        #         if isinstance(value._[0], int):
        #             value._ = [rf'{name}_{x}' for x in range(value._[0])]
        #             value.ordered = True

        #         # if not assume string and make a set of things
        #         # with the same name, and set them on the program
        #         for n, x in enumerate(value._):
        #             if x in self.things:
        #                 # if thing already declared as part of another index
        #                 # update her parent
        #                 thng: X = self.things[self.things.index(x)]
        #                 thng.parent.append(value)
        #                 value._[n] = thng
        #             else:
        #                 # else make a new thing
        #                 # and set it on the program
        #                 thng = X(value)
        #                 value._[n] = thng
        #                 setattr(self, x, thng)

        #     if isinstance(value, X):
        #         # only new things are set, see setattr for I
        #         value.number = len(self.things)
        #         self.things.append(value)

        #     if isinstance(value, V):
        #         value.number = len(self.variables)
        #         self.variables.append(value)
        #         vargs = {
        #             'name': value.name,
        #             'itg': value.itg,
        #             'nn': value.nn,
        #             'bnr': value.bnr,
        #         }
        #         for n, i in enumerate(value.idx()):
        #             if isinstance(i, tuple):
        #                 value.vars.append(V(*i, **vargs))
        #             else:
        #                 value.vars.append(V(i, **vargs))
        #             value.vars[n].parent = value
        #             value.vars[n].number = self.n_var
        #             self.n_var += 1

        #         if value.itg:
        #             # integer variable
        #             self.vars_itg.append(value)

        #         if value.nn:
        #             # non negative variable
        #             self.vars_nn.append(value)

        #         else:
        #             # continuous variable
        #             self.vars_cnt.append(value)

        #     if isinstance(value, P):
        #         value.number = len(self.parameters)
        #         self.parameters.append(value)

        #         for n, i in enumerate(value.idx()):
        #             if isinstance(i, tuple):
        #                 value.pars.append(P(*i, name=value.name, _=[value._[n]]))
        #             else:
        #                 value.pars.append(P(i, name=value.name, _=[value._[n]]))
        #             value.pars[n].parent = value
        #             value.pars[n].number = self.n_par
        #             self.n_par += 1

        #         # if parameter has index
        #         # generate parameters for each index

        #     if isinstance(value, T):
        #         self.thetas.append(value)
        #         if value.index:
        #             for n, i in enumerate(value.idx()):
        #                 value._[n] = T(*i, name=value.name, _=value._[n])
        #                 value._[n].mum = value

        #     # relational elements
        #     if isinstance(value, F):
        #         value.number = len(self.functions)
        #         self.functions.append(value)

        #         for n, i in enumerate(value.idx()):
        #             if isinstance(i, tuple):
        #                 value.funs.append(
        #                     F(one=value.one(*i), rel=value.rel, two=value.two(*i))
        #                 )
        #             else:
        #                 value.funs.append(
        #                     F(one=value.one(i), rel=value.rel, two=value.two(i))
        #                 )
        #             value.funs[n].parent = value
        #             value.funs[n].number = self.n_fun
        #             self.n_fun += 1

        #     if isinstance(value, C):
        #         value.number = len(self.constraints)
        #         self.constraints.append(value)
        #         if self.canonical:
        #             value.canoncial(
        #                 P(
        #                     *value.index,
        #                     _=[Z(_=self.tol) for _ in range(len(value))],
        #                     name='δ',
        #                 )
        #             )
        #             for n, i in enumerate(value.rhs.idx()):
        #                 if isinstance(i, tuple):
        #                     value.rhs.pars.append(
        #                         P(*i, name=value.rhs.name, _=[value.rhs._[n]])
        #                     )
        #                 else:
        #                     value.rhs.pars.append(
        #                         P(i, name=value.rhs.name, _=[value.rhs._[n]])
        #                     )
        #                 value.rhs.pars[n].parent = value.rhs
        #         if len(value) == 1:
        #             value.cons = [value]

        #         else:
        #             for n, i in enumerate(value.idx()):

        #                 if isinstance(i, tuple):
        #                     value.cons.append(
        #                         C(lhs=value.lhs(*i), rel=value.rel, rhs=value.rhs(*i))
        #                     )
        #                 else:
        #                     value.cons.append(
        #                         C(lhs=value.lhs(i), rel=value.rel, rhs=value.rhs(i))
        #                     )
        #                 value.cons[n].parent = value
        #                 value.cons[n].number = self.n_con
        #                 self.n_con += 1

        #     if isinstance(value, O):
        #         self.objectives.append(value)
        #         value.count = len(self.objectives)

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
    def index(self):
        """Set of all indices"""
        return I(product(*[s._ if isinstance(s, I) else [s] for s in self.indices]))

    @property
    def dim(self):
        """Dimension of the program"""
        return len(self.indices)

    # @property
    # def dscr(self):
    #     """things"""
    #     return len(self.things)

    def pyomo(self):
        """Return Pyomo Model"""

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
