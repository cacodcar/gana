"""An Ordered Set
Forms the base for all element sets 
"""

from abc import ABC, abstractmethod
from math import prod
from IPython.display import Math, display

from ..elements.idx import Idx
from .index import I


class Set(ABC):
    """An Ordered Set"""

    def __init__(self, *index: I | Idx):
        # index of the set
        self.index = list(index)

        self.name: str = None

        # number of index set
        self.n: int = None

    @abstractmethod
    def _(self):
        """Elements of the Set"""

    @abstractmethod
    def latex(self) -> str:
        """LaTeX representation"""

    @abstractmethod
    def sympy(self):
        """Symbolic representation"""

    def matrix(self):
        """Matrix Representation"""
        return [e.matrix() for e in self._()]

    def idx(self) -> list[tuple]:
        """index"""
        return [(i,) if not isinstance(i, tuple) else i for i in prod(self.index)._()]

    def pprint(self) -> Math:
        """Display the function"""
        for e in self._():
            display(Math(e.latex()))

    def __len__(self):
        return len(self.idx())

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))
