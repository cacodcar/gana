"""An index"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self


if TYPE_CHECKING:
    from ..sets.index import I


class Skip:
    """A Skip"""

    def __init__(self):
        self.name = 'skip'

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

    def __init__(self, name: str | int | tuple[Self]):

        if isinstance(name, tuple) and all([isinstance(i, (Idx, Skip)) for i in name]):
            self.name = rf'({", ".join([i.name.replace('(', '').replace(')', '') for i in name])})'
            self._ = list(name)
        else:
            if not isinstance(name, (str, int, Skip)):
                raise ValueError('Index name must be a string or integer')
            self.name = rf'{name}'
            self._ = [name]

        # an index can belong to multiple index sets
        # hence has multiple parents and positions in them
        self.parent: list[I] = []
        self.pos: list[int] = []
        # n is only taken when declared first time
        self.n: int = None

    def skip(self):
        """Skip an index"""
        if any([isinstance(i, Skip) for i in self._]):
            return True

    def order(self):
        """Order of the index"""
        return len(self._)

    def latex(self):
        """Latex representation"""

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
