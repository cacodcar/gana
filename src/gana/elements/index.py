"""An index"""

from __future__ import annotations

from typing import Self, TYPE_CHECKING

from .element import X

if TYPE_CHECKING:
    from ..sets.indices import I


class Idx(X):
    """An index"""

    def __init__(self, parent: list[I], name: str = None, pos: int = None):
        self._ = [self]

        super().__init__(parent=parent, pos=pos)
        self.name = name
        # an index can belong to multiple index sets
        if not isinstance(self.parent, list):
            self.parent = [self.parent]
            self.pos = [self.pos]

    def __eq__(self, other: Self):
        if isinstance(other, Idx):
            return self.name == other.name
        return self.name == other

    def __mul__(self, other: Self):
        if isinstance(other, Idx):
            if sorted(set(self.parent) | set(other.parent), key=str) != sorted(
                self.parent + other.parent, key=str
            ):
                raise ValueError(
                    f'{other} can only belong at one index of element.',
                    f'{other} also in {self}',
                )
        if other == 1:
            return self

        return NotImplemented

    def __rmul__(self, other: Self):
        return self * other
