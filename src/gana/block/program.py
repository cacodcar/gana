"""Mathematical Program"""

from dataclasses import dataclass, field
from itertools import product
from typing import Self
from warnings import warn

from IPython.display import display

from ..sets.parameter import P
from ..sets.index import I
from ..sets.theta import T
from ..sets.variable import V
from ..sets.constraint import C
from ..sets.function import F
from ..sets.objective import O
from ..sets.thing import X
from ..value.zero import Z


@dataclass
class Prg:
    """A mathematical program"""

    name: str = field(default=':p:')
    tol: float = field(default=None)
    canonical: bool = field(default=True)

    def __post_init__(self):
        # names of declared modeling and relational elements
        self.names = []

        # modeling elements
        (
            self.indices,
            self.things,
            self.variables,
            self.vars_cnt,
            self.vars_itg,
            self.vars_nn,
            self.vars_bnr,
            self.parameters,
            self.thetas,
            self.functions,
            self.constraints,
            self.objectives,
        ) = ([] for _ in range(12))

        # counts of variable, parameter, constraint, function, objective
        self.n_var, self.n_par, self.n_con, self.n_fun, self.n_obj = (
            0 for _ in range(5)
        )

    def __setattr__(self, name, value) -> None:

        # Collect names here
        # Things (X) can belong to multiple indices
        # Hence they can be overwritten
        if isinstance(value, (I, X, V, P, T, F, C, O)):

            if name[-1] == '_':
                warn(
                    'Ending name with underscore is not recommended, can cause printing issues'
                )

            if not isinstance(value, X) and name in self.names:
                warn(f'Overwriting {name}')
            value.name = name
            self.names.append(name)

        if isinstance(value, I):
            self.indices.append(value)
            value.number = len(self.indices)

            # if only a single integer is passed
            # create an orderd set of that length
            if isinstance(value._[0], int):
                value._ = [rf'{name}_{x}' for x in range(value._[0])]
                value.ordered = True

            # if not assume string and make a set of things
            # with the same name, and set them on the program
            for n, x in enumerate(value._):
                if x in self.things:
                    # if thing already declared as part of another index
                    # update her parents
                    thng: X = self.things[self.things.index(x)]
                    thng.parents.append(value)
                    value._[n] = thng
                else:
                    # else make a new thing
                    # and set it on the program
                    thng = X(value)
                    value._[n] = thng
                    setattr(self, x, thng)

        if isinstance(value, X):
            # only new things are set, see setattr for I
            value.number = len(self.things)
            self.things.append(value)

        if isinstance(value, V):
            value.number = len(self.variables)
            self.variables.append(value)
            vargs = {
                'name': value.name,
                'itg': value.itg,
                'nn': value.nn,
                'bnr': value.bnr,
            }
            for n, i in enumerate(value.idx()):
                if isinstance(i, tuple):
                    value.vars.append(V(*i, **vargs))
                else:
                    value.vars.append(V(i, **vargs))
                value.vars[n].parent = value
                value.vars[n].number = self.n_var
                self.n_var += 1

            if value.itg:
                # integer variable
                self.vars_itg.append(value)

            if value.nn:
                # non negative variable
                self.vars_nn.append(value)

            else:
                # continuous variable
                self.vars_cnt.append(value)

        if isinstance(value, P):
            value.number = len(self.parameters)
            self.parameters.append(value)

            for n, i in enumerate(value.idx()):
                if isinstance(i, tuple):
                    value.pars.append(P(*i, name=value.name, _=[value._[n]]))
                else:
                    value.pars.append(P(i, name=value.name, _=[value._[n]]))
                value.pars[n].parent = value
                value.pars[n].number = self.n_par
                self.n_par += 1

            # if parameter has index
            # generate parameters for each index

        if isinstance(value, T):
            self.thetas.append(value)
            if value.index:
                for n, i in enumerate(value.idx()):
                    value._[n] = T(*i, name=value.name, _=value._[n])
                    value._[n].mum = value

        # relational elements
        if isinstance(value, F):
            value.number = len(self.functions)
            self.functions.append(value)

            for n, i in enumerate(value.idx()):
                if isinstance(i, tuple):
                    value.funs.append(
                        F(one=value.one(*i), rel=value.rel, two=value.two(*i))
                    )
                else:
                    value.funs.append(
                        F(one=value.one(i), rel=value.rel, two=value.two(i))
                    )
                value.funs[n].parent = value
                value.funs[n].number = self.n_fun
                self.n_fun += 1

        if isinstance(value, C):
            value.number = len(self.constraints)
            self.constraints.append(value)
            if self.canonical:
                value.canoncial(
                    P(
                        *value.index,
                        _=[Z(_=self.tol) for _ in range(len(value))],
                        name='δ',
                    )
                )
                for n, i in enumerate(value.rhs.idx()):
                    if isinstance(i, tuple):
                        value.rhs.pars.append(
                            P(*i, name=value.rhs.name, _=[value.rhs._[n]])
                        )
                    else:
                        value.rhs.pars.append(
                            P(i, name=value.rhs.name, _=[value.rhs._[n]])
                        )
                    value.rhs.pars[n].parent = value.rhs
            if len(value) == 1:
                value.cons = [value]

            else:
                for n, i in enumerate(value.idx()):

                    if isinstance(i, tuple):
                        value.cons.append(
                            C(lhs=value.lhs(*i), rel=value.rel, rhs=value.rhs(*i))
                        )
                    else:
                        value.cons.append(
                            C(lhs=value.lhs(i), rel=value.rel, rhs=value.rhs(i))
                        )
                    value.cons[n].parent = value
                    value.cons[n].number = self.n_con
                    self.n_con += 1

        if isinstance(value, O):
            self.objectives.append(value)
            value.count = len(self.objectives)

        super().__setattr__(name, value)

    def combine(self, *prgs: tuple[Self]):
        """Club Programs"""
        for prg in prgs:
            if isinstance(prg, Prg):
                # modeling elements
                self.indices = self.indices + prg.indices
                self.variables = self.variables + prg.variables
                self.vars_cnt = self.vars_cnt + prg.vars_cnt
                self.vars_itg = self.vars_itg + prg.vars_itg
                self.vars_nn = self.vars_nn + prg.vars_nn
                self.vars_bnr = self.vars_bnr + prg.vars_bnr
                self.thetas = self.thetas + prg.thetas
                self.parameters = self.parameters + prg.parameters
                self.functions = self.functions + prg.functions
                self.constraints = self.constraints + prg.constraints
                self.objectives = self.objectives + prg.objectives

    @property
    def index(self):
        """Set of all indices"""
        return I(product(*[s._ if isinstance(s, I) else [s] for s in self.indices]))

    @property
    def dim(self):
        """Dimension of the program"""
        return len(self.indices)

    @property
    def dscr(self):
        """things"""
        return len(self.things)

    def matrix(self):
        """Return Matrix Representation"""

    def pyomo(self):
        """Return Pyomo Model"""

    def mps(self):
        """Return MPS File"""

    def lp(self):
        """Return LP File"""

    def latex(self):
        """Display LaTeX"""

        for s in self.indices:
            display(s.latex())

        for e in self.constraints + self.objectives:
            display(e.latex())

    def pprint(self, descriptive: bool = False):
        """Pretty Print"""

        for i in self.indices:
            i.pprint(True)

        for c in self.constraints + self.objectives:
            c.pprint(descriptive)

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))
