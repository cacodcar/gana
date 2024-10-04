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


@dataclass
class Prg:
    """A mathematical program"""

    name: str = field(default=':p:')

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

    def __setattr__(self, name, value) -> None:

        # modeling elements
        if isinstance(value, (I, X, V, P, T, F, C, O)):
            if not isinstance(value, X) and name in self.names:
                warn(f'Overwriting {name}')
            value.name = name
            self.names.append(name)

        if isinstance(value, I):
            self.indices.append(value)
            value.number = len(self.indices)
            if isinstance(value._, int):
                for x in range(value._):
                    setattr(self, f'{name}{x}', X(value))
            else:
                for x in value._:
                    setattr(self, x, X(value))

        if isinstance(value, X):
            print(self.things)
            print(name)
            if name in self.things:
                print('here')
                thng = getattr(self, name)
                print('thng', thng)
                print('thingno', thng.number)
                value.parents.extend(thng.parents)
                value.number = thng.number
                self.things[thng.number] = value
            else:
                value.number = len(self.things)
                self.things.append(value)

        if isinstance(value, V):
            self.variables.append(value)
            value.count = len(self.variables)
            # if variable has index
            # generate variables for each index
            if value.index:
                for n, i in enumerate(value.idx()):
                    value._.append(V(*i, name=value.name, itg=value.itg, nn=value.nn))
                    value._[n].mum = value

            if value.itg:
                # integer variable
                self.vars_itg.append(value)

            if value.nn:
                # non negative variable
                self.vars_nn.append(value)

            else:
                # continuous variable
                self.vars_cnt.append(value)
            # if variable is non negative
            # if value.nn:
            # setattr(self, f'{value}^0', P(*value.index, _=0))
            # setattr(self, f'{value}_nn', value >= getattr(self, f'{value}^0'))

        if isinstance(value, P):
            self.parameters.append(value)
            value.count = len(self.parameters)

            # if parameter has index
            # generate parameters for each index
            if value.index:
                for n, i in enumerate(value.idx()):
                    value._[n] = P(*i, name=value.name, _=[value._[n]])
                    value._[n].mum = value

        if isinstance(value, T):
            self.thetas.append(value)
            if value.index:
                for n, i in enumerate(value.idx()):
                    value._[n] = T(*i, name=value.name, _=value._[n])
                    value._[n].mum = value

        # relational elements
        if isinstance(value, F):
            self.functions.append(value)
            value.count = len(self.functions)

        if isinstance(value, C):
            self.constraints.append(value)
            value.count = len(self.constraints)

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

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    # def __getitem__(self, key: int | tuple):

    #     if isinstance(key, tuple):
    #         return self.index[self.idx().index(key)]

    #     if isinstance(key, int):
    #         return self.index[key]

    def __call__(self):

        for s in self.indices:
            display(s(True))

        for e in self.constraints + self.objectives:
            display(e())
