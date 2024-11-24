"""Index elements 
Skip - do not use the index
Idx - index
Pair - pair of indices

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self


if TYPE_CHECKING:
    from ..sets.index import I

    # from ..sets.parameter import P
    # from ..sets.variable import V


class Skip:
    """A Skip"""

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

    def __init__(self, name: str | int, parent: I, pos: int, inorder: bool = False):

        self._name = str(name)

        if inorder:
            self._parent: I = parent
            self._pos: int = pos
        else:
            # In an ordered set of indices
            # an index can belong to multiple index sets
            # hence has multiple parents and positions in them
            self._parent: list[I] = [parent]
            self._pos: list[int] = [pos]

        self.inorder = inorder

        # n is only taken when declared first time
        self.n: int = None

    @property
    def name(self):
        """Name of the index"""
        if self.inorder:
            return f'{self.parent}{self._name}'
        return self._name

    @property
    def parent(self):
        """Parent of the index"""
        if self.inorder:
            return self._parent
        return [p for p in self._parent if p.name]

    @property
    def pos(self):
        """Position of the index"""
        if self.inorder:
            return self._pos
        return [p for p, par in zip(self._pos, self._parent) if par.name]

    def update(self, parent: I, pos: int):
        """Update the parent and position of the index"""
        self._parent.append(parent)
        self._pos.append(pos)
        return self

    # def skip(self):
    #     """Skip an index"""
    #     if any([isinstance(i, Skip) for i in self._]):
    #         return True

    def latex(self):
        """Latex representation"""
        # TODO - put \in parents with \cup

        if self.parent[0].ordered:
            return self.pos[0]
        return rf'{self.name}'

    def __eq__(self, other: Self | int):
        if self.inorder and isinstance(other, int):
            return self._pos == other
        return self.name == str(other)

    def __and__(self, other: Self):
        if isinstance(other, Skip):
            return Skip()
        return Pair(self, other)

    def __rand__(self, other: Self):
        if isinstance(other, Skip):
            return Skip()
        return Pair(other, self)

    def __rmul__(self, other: int):
        return self

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))


class Pair:
    """A pair of indices
    Can be a nested, so essentially a tuple
    """

    def __init__(self, i: Idx, j: Idx):
        self.i = i
        self.j = j

        self.name = rf'{tuple(self._)}'

    @property
    def _(self) -> list[Idx]:
        """Constituent index elements (Idx)"""
        return sum(
            [idx._ if isinstance(idx, Pair) else [idx] for idx in [self.i, self.j]], []
        )

    @property
    def parent(self) -> list[I]:
        """Parents of constituent index elements"""
        return [idx.parent for idx in self._]

    @property
    def pos(self) -> list[int]:
        """Positions of constituent index elements"""
        return [idx.pos for idx in self._]

    @property
    def nested(self):
        """If this is a nested pair"""
        if len(self._) > 2:
            return True

    def order(self):
        """Order of the index"""
        return len(self._)

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other: Self):
        for i, j in zip(self, other):
            if i != j:
                return False
        return True

    def __and__(self, other: Self):
        if isinstance(other, Skip):
            return Skip()
        return Pair(self, other)

    def __rand__(self, other: Self):
        if isinstance(other, Skip):
            return Skip()
        return Pair(other, self)

    def __getitem__(self, pos: int) -> Idx:
        return self._[pos]

    def __iter__(self):
        return iter(self._)
