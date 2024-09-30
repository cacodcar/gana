"""Mathematical Program"""

from dataclasses import dataclass, field
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
        self.sets: list[S] = []

        self.variables: list[V] = []
        self.contvars: list[V] = []
        self.intvars: list[V] = []
        self.parameters: list[P] = []

        self.mpvars: list[T] = []

        # relational elements
        self.functions: list[F] = []
        self.constraints: list[C] = []
        self.objectives: list[O] = []

        # names of declared modeling and relational elements
        self.names: list[str] = []

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
            'contvars',
            'intvars',
            'parameters',
            'mpvars',
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
            self.variables.append(value)
            value.count = len(self.variables)

            # if variable has index
            # generate variables for each index
            if value.index:
                for n, i in enumerate(value.idx()):
                    value._.append(V(*i, name=value.name, itg=value.itg, nn=value.nn))
                    value._[n].mum = value
                    value._[n].count = self._n_v
                    self._n_v += 1

            if value.itg:
                # integer variable
                self.intvars.append(value)

            else:
                # continuous variable
                self.contvars.append(value)

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
                    value._[n].count = self._n_p
                    self._n_p += 1
                # for p in value._:
                #     p.mum = value

        if isinstance(value, T):
            self.mpvars.append(value)

            if value.index:
                for n, i in enumerate(value.idx()):
                    value._[n] = T(*i, name=value.name, _=value._[n])
                    value._[n].mum = value
                    value._[n].count = self._n_t
                    self._n_t += 1

        # relational elements
        if isinstance(value, F):
            self.functions.append(value)

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
            self.sets = list(set(self.sets) | set(prg.sets))
            self.variables = list(set(self.variables) | set(prg.variables))
            self.contvars = list(set(self.contvars) | set(prg.contvars))
            self.intvars = list(set(self.intvars) | set(prg.intvars))
            self.parameters = list(set(self.parameters) | set(prg.parameters))
            self.parameters = list(set(self.parameters) | set(prg.parameters))
            self.mpvars = list(set(self.mpvars) | set(prg.mpvars))

            # relational elements
            self.functions = list(set(self.functions) | set(prg.functions))
            self.constraints = list(set(self.constraints) | set(prg.constraints))
            self.objectives = list(set(self.objectives) | set(prg.objectives))

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
        for e in self.constraints + self.objectives:
            display(e.latex())

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __call__(self):
        for e in self.constraints + self.objectives:
            display(e())
