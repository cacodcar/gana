"""Mathematical Program"""

from dataclasses import dataclass, field
from typing import Self
from warnings import warn

from IPython.display import Math, display
from sympy import latex

from ..element.p import P
from ..element.s import S
from ..element.t import T
from ..element.v import V
from ..element.x import X
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
        self.variables: list[V | X] = []
        self.continuous: list[V] = []
        self.binary: list[X] = []
        self.parameters: list[P] = []
        self.thetas: list[T] = []

        # relational elements
        self.functions: list[F] = []
        self.constraints: list[C] = []
        self.objectives: list[O] = []

        # names of declared modeling and relational elements
        self.names: list[str] = []

    def __setattr__(self, name: str, value: V) -> None:

        if not name in [
            'name',
            'overwrite',
            'sets',
            'variables',
            'continuous',
            'binary',
            'parameters',
            'thetas',
            'functions',
            'constraints',
            'objectives',
            'names',
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
        if isinstance(value, S | V | X | P | T | F | C | O):
            value.name = name

        if isinstance(value, S):
            self.sets.append(value)

        if isinstance(value, V | X):
            self.variables.append(value)

            if isinstance(value, V):
                self.continuous.append(value)

            if isinstance(value, X):
                self.binary.append(value)

        if isinstance(value, P):
            self.parameters.append(value)

        if isinstance(value, T):
            self.thetas.append(value)

        # relational elements
        if isinstance(value, F):
            self.functions.append(value)

        if isinstance(value, C):
            self.constraints.append(value)

        if isinstance(value, O):
            self.objectives.append(value)

        super().__setattr__(name, value)

    def club(self, prg: Self):
        """Club two Programs"""
        if isinstance(prg, Prg):

            # modeling elements
            self.sets = list(set(self.sets) | set(prg.sets))
            self.variables = list(set(self.variables) | set(prg.variables))
            self.continuous = list(set(self.continuous) | set(prg.continuous))
            self.binary = list(set(self.binary) | set(prg.binary))
            self.parameters = list(set(self.parameters) | set(prg.parameters))
            self.parameters = list(set(self.parameters) | set(prg.parameters))
            self.thetas = list(set(self.thetas) | set(prg.thetas))

            # relational elements
            self.functions = list(set(self.functions) | set(prg.functions))
            self.constraints = list(set(self.constraints) | set(prg.constraints))
            self.objectives = list(set(self.objectives) | set(prg.objectives))

    def eqns(self):
        """Return all equations"""
        for c in self.constraints:
            yield c.sym

    def pprint(self):
        """Pretty prints the component"""
        for e in self.eqns():
            display(Math(latex(e, mul_symbol='dot')))

    def latex(self):
        """Returns the latex"""
        for e in self.eqns():
            display(latex(e, mul_symbol='dot'))

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)
