"""Mathematical Program"""

from dataclasses import dataclass, field
from warnings import warn
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

        if name != 'name' and value:
            if name in self.names:
                if self.overwrite:
                    warn(f'Overwriting {name}')
                else:
                    raise ValueError(
                        f'{name} is already defined, set overwrite=True to allow overwriting'
                    )

            self.names.append(name)

        if isinstance(value, V | X | S | P):
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
