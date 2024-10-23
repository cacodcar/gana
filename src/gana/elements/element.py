"""An element in a set"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..sets.ordered import Set


class X:
    """A Member of an Ordered Set"""

    def __init__(self, pos: int = None, parent: Set = None):

        # name of the element
        if hasattr(parent, 'name'):
            self.name = parent.name + rf'_{pos}'
        else:
            self.name = 'X'

        # ordered set to which the element belongs
        self.parent = parent

        # position in the ordered
        # ordinality
        self.pos = pos

        # position in the problem
        self.n = None

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __len__(self):
        return 1

    def __init_subclass__(cls):
        cls.__repr__ = X.__repr__
        cls.__hash__ = X.__hash__
