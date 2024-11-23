"""An Ordered Set
Forms the base for all element sets 
"""

from math import prod

from ..elements.idx import Idx
from .index import I


class Set:
    """An ordered Element Set"""

    def __init__(self, *index: tuple[Idx | int | I]):

        index = tuple([Idx(i) if isinstance(i, int) else i for i in index])

        if all([isinstance(i, Idx) for i in index]):
            if len(index) == 1:
                index = index[0]
            self.index = I(index)
            # self.index.of.append((0, self))
        else:
            # for n, idx in enumerate(index):
            #     idx.of.append((n, self))
            self.index: I = prod(index)

        # if not self.index.name:
        #     self.index.name = f'{index}'

        # name is set by the program
        self.name = ''
        # number of the set in the program
        self.n: int = None

        if self.index:
            self.idx = {i: n for n, i in enumerate(self.index._)}

        else:
            self.idx = {}

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
