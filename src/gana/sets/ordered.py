"""An Ordered Set
Forms the base for all element sets 
"""

from math import prod

from ..elements.index import Idx
from .index import I


class Set:
    """An ordered Element Set"""

    def __init__(self, *index: tuple[Idx | I]):

        self.index = index

        # name is set by the program
        self.name = ''
        # number of the set in the program
        self.n: int = None

        if self.index:
            self.idx = {i: n for n,i in enumerate(self.index._)}
        else:
            self.idx = {}

    def __setattr__(self, name, value):
    
        if name == 'index' and value: 

            if all([isinstance(i, (Idx, int)) for i in value]):
                value = tuple([Idx(i) if isinstance(i, int) else i for i in value])
                if len(value) == 1:
                    value = value[0]
                value = I(value)
            else:
                value: I = prod(value)

        super().__setattr__(name, value)

    def nsplit(self):
        """Split the name"""
        if '_' in self.name:
            name, sup = self.name.split('_')
            return name, r'^{' + sup + r'}'
        return self.name, ''


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
