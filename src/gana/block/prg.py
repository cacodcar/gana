"""Mathematical Program"""

from IPython.display import Math, display
from dataclasses import dataclass, field
from typing import Self
from warnings import warn

from sympy import latex

from ..element.v import V
from ..element.s import S
from ..element.x import X
from ..element.p import P

from ..relational.f import F
from ..relational.c import C
from ..relational.o import O


@dataclass
class Prg:
    """A mathematical program"""

    name: str = field(default='Program')
    overwrite: bool = field(default=False)

    def __post_init__(self):
        self.sets: list[S] = []
        self.variables: list[V | X] = []
        self.continuous: list[V] = []
        self.binary: list[X] = []
        self.parameters: list[P] = []
        self.functions: list[F] = []
        self.constraints: list[C] = []
        self.objectives: list[O] = []

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

        if isinstance(value, V | X | S | P | F | C | O):
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

        if isinstance(value, F):
            self.functions.append(value)

        if isinstance(value, C):
            self.constraints.append(value)

        if isinstance(value, O):
            self.objectives.append(value)

        super().__setattr__(name, value)

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def club(self, prg: Self):
        """Club two Programs"""
        if isinstance(prg, Prg):

            self.sets = list(set(self.sets) | set(prg.sets))
            self.variables = list(set(self.variables) | set(prg.variables))
            self.continuous = list(set(self.continuous) | set(prg.continuous))
            self.binary = list(set(self.binary) | set(prg.binary))
            self.parameters = list(set(self.parameters) | set(prg.parameters))
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
