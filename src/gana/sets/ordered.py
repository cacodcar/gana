"""An Ordered Set
Forms the base for all element sets 
"""

from math import prod
from .index import I


class Set:
    """An ordered Element Set"""

    def __init__(self, *index: tuple[I]):

        self.index: I = prod(index)

        self.name = ''
        # number of the set in the program
        self.n: int = None

    def nsplit(self):
        """Split the name"""
        if '_' in self.name:
            name, sup = self.name.split('_')
            return name, r'^{' + sup + r'}'
        return self.name, ''

    def latex(self) -> str:
        """LaTeX representation"""
        name, sup = self.nsplit()

        return (
            name
            + sup
            + r'_{'
            + rf'{self.index}'.replace('(', '').replace(')', '')
            + r'}'
        )

    def order(self) -> list:
        """order"""
        return len(self.index)

    def __len__(self):
        return len(self.index._)

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __init_subclass__(cls):
        cls.__repr__ = Set.__repr__
        cls.__hash__ = Set.__hash__
