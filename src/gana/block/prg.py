"""Mathematical Program"""

from dataclasses import dataclass, field
from itertools import product
from typing import Self
from warnings import warn

from IPython.display import display

from ..element.p import P
from ..element.s import S
from ..element.t import T
from ..element.v import V
from ..relational.c import C
from ..relational.f import F
from ..relational.o import O


@dataclass
class Prg:
    """A mathematical program"""

    name: str = field(default='Program')
    overwrite: bool = field(default=False)

    def __post_init__(self):

        # modeling elements
        (
            self.sets,
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

        # names of declared modeling and relational elements
        self.names = []

        # counts
        # A separate counter is needed because elements, i.e.:
        # (variables, parameters, constraints, objectives)
        # are indexed and are a set of elements as opposed to a single element
        self._n_t, self._n_v, self._n_p, self._n_c, self._n_o = (0 for _ in range(5))

    def __setattr__(self, name: str, value: V) -> None:

        if not name in [
            'name',
            'overwrite',
            'sets',
            'variables',
            'vars_cnt',
            'vars_itg',
            'vars_nn',
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
        if isinstance(value, S | V | P | T | F | C | O):
            value.name = name

        if isinstance(value, S):
            # set the counter on the element
            self.sets.append(value)
            value.count = len(self.sets)
            for n, s in enumerate(value._):
                if isinstance(s, (int, float)):
                    value._[n] = S(s, name=f'{value.name}_{n}')
                else:
                    value._[n] = S(s, name=str(s))

        if isinstance(value, V):
            self.variables += value
            value.count = len(self.variables)
            # if variable has index
            # generate variables for each index
            if value.index:
                for n, i in enumerate(value.idx()):
                    value._.append(V(*i, name=value.name, itg=value.itg, nn=value.nn))
                    value._[n].mum = value

            if value.itg:
                # integer variable
                self.vars_itg += value

            if value.nn:
                # non negative variable
                self.vars_nn += value

            
            else:
                # continuous variable
                self.vars_cnt += value
            # if variable is non negative
            # if value.nn:
            # setattr(self, f'{value}^0', P(*value.index, _=0))
            # setattr(self, f'{value}_nn', value >= getattr(self, f'{value}^0'))

        if isinstance(value, P):
            self.parameters += value
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
            self.functions += value
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
            self.sets += prg.sets
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
        return S(product(*[s._ if isinstance(s, S) else [s] for s in self.sets]))

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

        for s in self.sets:
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

        for s in self.sets:
            display(s())

        for e in self.constraints + self.objectives:
            display(e())
