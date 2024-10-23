"""An Ordered Set
Forms the base for all element sets 
"""

from math import prod


class Set:
    """An Ordered Set"""

    def __init__(self, *order, name: str = None):
        # index of the set
        self.order = order
        self.name = name
        # position of the set in the program
        self.n: int = None

    def idx(self) -> list[tuple]:
        """index"""

        if len(self.order) > 1:
            # Index Set
            return [i for i in prod(self.order)._]
        return self.order[0]._

    def ord(self) -> list:
        """order"""
        return len(self.order)

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
        if self.order:
            return True
