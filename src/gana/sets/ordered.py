"""An Ordered Set
Forms the base for all element sets 
"""

from abc import ABC, abstractmethod
from math import prod

from IPython.display import Math


class Set(ABC):
    """An Ordered Set"""

    def __init__(self, *order, name: str = None):
        # index of the set
        self.order = order
        self.name = name
        # order in Program
        self.n: int = None

    @abstractmethod
    def process(self):
        """Child of the set"""

    @abstractmethod
    def pprint(self) -> Math:
        """Display the function"""

    def idx(self) -> list[tuple]:
        """index"""
        if isinstance(self.order, int):
            return [(i,) for i in range(self.order)]

        if len(self.order) > 1:
            # Index Set
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

    def __bool__(self):
        return bool(self.name)
