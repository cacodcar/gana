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


@dataclass
class Prg:
    """A mathematical program"""

    name: str = field(default='Program')
    overwrite: bool = field(default=False)

    def __post_init__(self):
        # names of declared modeling and relational elements
        self.names = []

        # modeling elements
        (
            self.indices,
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
        ) = ([] for _ in range(11))

        # counts
        # A separate counter is needed because elements, i.e.:
        # (variables, parameters, constraints, objectives)
        # are indexed and are a set of elements as opposed to a single element
        self._n_t, self._n_v, self._n_p, self._n_c, self._n_o = (0 for _ in range(5))

    def __setattr__(self, name, value) -> None:

        if not name in [
            'name',
            'overwrite',
            'indices',
            'variables',
            'vars_cnt',
            'vars_itg',
            'vars_nn',
            'vars_bnr',
            'parameters',
            'thetas',
            'functions',
            'constraints',
            'objectives',
            'names',
            '_n_t',
            '_n_v',
            '_n_p',
            '_n_c',
            '_n_o',
        ]:
            if name in self.names:
                if self.overwrite:
                    warn(f'Overwriting {name}')
                else:
                    raise ValueError(
                        f'{name} is already defined, set overwrite=True to allow overwriting'
                    )
            self.names.append(name)

        # modeling elements
        if isinstance(value, (I, V, P, T, F, C, O)):
            value.name = name

        if isinstance(value, I):
            # set the counter on the element
            self.indices.append(value)
            value.count = len(self.indices)
            if isinstance(value._, list):
                for n, i in enumerate(value._):
                    if isinstance(i, (int, float, str)):
                        value._[n] = I(i, name=f'{i}')

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
                    value._[n] = P(*i, name=value.name, _=value._[n])
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

    def club(self, prg: Self):
        """Club two Programs"""
        if isinstance(prg, Prg):

            # modeling elements
            self.indices += prg.indices
            self.variables += prg.variables
            self.vars_cnt += prg.vars_cnt
            self.vars_itg += prg.vars_itg
            self.vars_nn += prg.vars_nn
            self.vars_bnr += prg.vars_bnr
            self.thetas += prg.thetas
            self.parameters += prg.parameters
            self.functions += prg.functions
            self.constraints += prg.constraints
            self.objectives += prg.objectives

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

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __getitem__(self, key: int | tuple):

        if isinstance(key, tuple):
            return self.index[self.idx().index(key)]

        if isinstance(key, int):
            return self.index[key]

    def __call__(self):

        for s in self.indices:
            display(s())

        for e in self.constraints + self.objectives:
            display(e())
