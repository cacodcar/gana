"""An index"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self


if TYPE_CHECKING:
    from ..sets.index import I
    from ..sets.parameter import P
    from ..sets.variable import V


class Skip:
    """A Skip"""

    def __init__(self):
        self.name = 'skip'
        self._parent: list[I] = []
        self._pos: list[int] = []

    def update(self, parent: I, pos: int):
        """Update the parent and position of the index"""
        self._parent.append(parent)
        self._pos.append(pos)
        return self

    def __mul__(self, other: Self):
        return self

    def __rmul__(self, other: Self):
        return self

    def __str__(self):
        return r'Skip'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))


class Idx:
    """An index"""

    def __init__(self, name: str | int | tuple[Self], parent: I, pos: int):

        if isinstance(name, tuple) and all([isinstance(i, (Idx, Skip)) for i in name]):
            self.name = rf'({", ".join([i.name.replace('(', '').replace(')', '') for i in name])})'
            self._ = list(name)
        else:
            if not isinstance(name, (str, int, Skip, float)):
                raise ValueError('Index name must be a string or integer or float')
            self.name = rf'{name}'
            self._ = [self]

        # an index can belong to multiple index sets
        # hence has multiple parents and positions in them
        self._parent: list[I] = [parent]
        self._pos: list[int] = [pos]
        # n is only taken when declared first time
        self.n: int = None

        # # index of what elements in the program
        # self.of: list[V | P] = []

    @property
    def parent(self):
        """Parent of the index"""
        return [p for p in self._parent if p.name]

    @property
    def pos(self):
        """Position of the index"""
        return [p for p, par in zip(self._pos, self._parent) if par.name]

    def update(self, parent: I, pos: int):
        """Update the parent and position of the index"""
        self._parent.append(parent)
        self._pos.append(pos)
        return self

    def skip(self):
        """Skip an index"""
        if any([isinstance(i, Skip) for i in self._]):
            return True

    def order(self):
        """Order of the index"""
        return len(self._)

    def latex(self):
        """Latex representation"""
        # TODO - put \in parents with \cup

        if self.parent[0].ordered:
            return self.pos[0]
        return rf'{self.name}'

    def __eq__(self, other: Self):
        if isinstance(other, Idx):
            return self.name == other.name
        return self.name == str(other)

    def __mul__(self, other: Self):
        if isinstance(other, int) and other == 1:
            return self
        return NotImplemented

    def __rmul__(self, other: Self):
        if isinstance(other, int) and other == 1:
            return self
        return NotImplemented

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __getitem__(self, pos: int) -> Idx:
        return self._[pos]
