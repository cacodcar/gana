"""An Ordered Set
Forms the base for all element sets 
"""

from abc import ABC, abstractmethod
from math import prod
from IPython.display import Math


class Set(ABC):
    """An Ordered Set"""

    def __init__(self, *order):
        # index of the set
        self.order = order
        self.name: str = None
        # number of index set
        self.n: int = None

        # set via the child method or taken as input
        self._ = []

    @abstractmethod
    def process(self):
        """Child of the set"""

    @abstractmethod
    def latex(self) -> str:
        """LaTeX representation"""

    @abstractmethod
    def sympy(self):
        """Symbolic representation"""

    @abstractmethod
    def matrix(self):
        """Matrix Representation"""

    @abstractmethod
    def pprint(self) -> Math:
        """Display the function"""
        # for e in self._:
        #     display(Math(e.latex()))

    def idx(self) -> list[tuple]:
        """index"""
        if len(self.order) > 1:
            return [i for i in prod(self.order)._]
        return self.order[0]._

    def __len__(self):
        return len(self.idx())

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __init_subclass__(cls):
        cls.__repr__ = Set.__repr__
        cls.__hash__ = Set.__hash__
