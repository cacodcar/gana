"""Mathematical Program"""

from dataclasses import dataclass, field
from ..element.v import V
from ..element.s import S

# from ..element.x import X
# from ..element.p import P


@dataclass
class Prg:
    """A mathematical program"""

    name: str = field(default='Program')

    def __post_init__(self):
        self.sets = []
        self.variables = []
        self.parameters = []
        self.constraints = []
        self.objectives = []

    def __setattr__(self, name: str, value: V) -> None:

        if isinstance(value, V | S):
            value.name = name

        if isinstance(value, V):
            self.variables.append(value)

        if isinstance(value, S):
            self.sets.append(value)

        super().__setattr__(name, value)

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)
