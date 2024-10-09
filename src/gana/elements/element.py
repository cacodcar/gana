"""An element in a set"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..sets.ordered import Set


class X:
    """A Member of an Ordered Set"""

    def __init__(self, parent: list[Set], name: str = None, n: int = None):
        # ordered set to which the element belongs
        if not isinstance(parent, list):
            parent = [parent]

        self.parent = parent

        # name of the element
        self.name = name

        # position in the ordered set
        self.n = n

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __len__(self):
        return 1