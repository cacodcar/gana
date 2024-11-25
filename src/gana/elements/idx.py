"""Index elements 
Skip - do not use the index
X - index element
Idx - Tuple of index elements

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self, Any


if TYPE_CHECKING:
    from ..sets.index import I


class Skip:
    """Skips the generation of model element at this index"""

    # multiplication of skip with anything is skip
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


class X:
    """A single element of an index

    A tuple of index elements (X) and (or) Skips form an index (Idx)

    """

    def __init__(self, name: Any, parent: I, pos: int = None, ordered: bool = False):

        # anything that can be represeted as a string should be good
        # will throw an error if not
        # hence not running instance check
        self._name = str(name)

        # Index sets (I) are of two types
        # 1. Ordered - integers
        # 2. unordered - strings

        # ordered index elements are numbers which reside in the set itself
        # for example 0 can be zeroth hour or zeroth day in a problem
        # so h_0 will only belong to the set of hours, and d_0 in days
        if ordered:
            # hence the parent is the set itself
            self._parent: I = parent
            # position is literally the position of the index in the set
            # which is given by the name (number itself)
            self._pos: int = name  #
        # unordered index elements are strings which can belong to multiple sets
        # Tool for example can belong to the set of progressive metal bands
        # as well as the set of Grammy winners
        else:
            # hence has multiple parents
            self._parent: list[I] = [parent]
            # and positions need to be specified
            self._pos: list[int] = [pos]

        self.ordered = ordered

        # this is the order of declaration in the program
        # for unordered index elements
        # n is only taken when declared first time
        self.n: int = None

    @property
    def name(self):
        """Name of the index element"""
        # if ordered takes the name from the parent
        if self.ordered:
            return f'{self.parent}{self._name}'
        # else the name which was given as a string anyway
        return self._name

    @property
    def parent(self):
        """Parent of the index element"""
        if self.ordered:
            return self._parent
        # when doing compound operations, intermediate parent sets are generated
        # This check excluses them
        return [p for p in self._parent if p.name]

    @property
    def pos(self):
        """Position of the index element in the index set (I)"""
        if self.ordered:
            return self._pos
        return [p for p, par in zip(self._pos, self._parent) if par.name]

    def update(self, parent: I, pos: int):
        """Update the parent and position of the index element"""
        # only used for unordered indices
        # no need to run check, because append will exclude the ordered indices anyway
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

        if self.ordered:
            return self.pos[0]
        return rf'{self.name}'

    def __eq__(self, other: Self | int):
        if self.ordered and isinstance(other, int):
            return self._pos == other
        return self.name == str(other)

    def __and__(self, other: Self):
        if isinstance(other, Skip):
            return Skip()
        return Idx(self, other)

    def __rand__(self, other: Self):
        if isinstance(other, Skip):
            return Skip()
        return Idx(other, self)

    def __add__(self, other: Self):
        if isinstance(other, Skip):
            return Skip()
        return Pair(self, other)

    def __radd__(self, other: Self):
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


class Idx:
    """A tuple of index elements
    A nested pair of index elements
    """

    def __init__(self, one: X, two: X):
        self.one = one
        self.two = two

        self.name = rf'{tuple(self._)}'

    @property
    def _(self) -> list[X]:
        """Constituent index elements (X)"""
        return sum(
            [idx._ if isinstance(idx, Idx) else [idx] for idx in [self.one, self.two]],
            [],
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
        for one, two in zip(self, other):
            if one != two:
                return False
        return True

    def __and__(self, other: Self):
        if isinstance(other, Skip):
            return Skip()
        return Idx(self, other)

    def __rand__(self, other: Self):
        if isinstance(other, Skip):
            return Skip()
        return Idx(other, self)

    def __add__(self, other: Self | Pair):
        if isinstance(other, Skip):
            return Skip()
        return Pair(self, other)

    def __radd__(self, other: Self | Pair):
        if isinstance(other, Skip):
            return Skip()
        return Pair(other, self)

    def __getitem__(self, pos: int) -> X:
        return self._[pos]

    def __iter__(self):
        return iter(self._)


class Pair:
    """Multi-Index for functions
    A nested pair of indices (Idx)
    """

    def __init__(self, one: Idx, two: Idx):
        self.one = one
        self.two = two

        self.name = rf'{self._}'

    @property
    def _(self) -> list[Idx]:
        """Constituent indices (Idx)"""
        return [self.one, self.two]

    @property
    def parent(self) -> list[I]:
        """Parents of constituent indices"""
        return [idx.parent for idx in self._]

    @property
    def pos(self) -> list[int]:
        """Positions of constituent indices"""
        return [idx.pos for idx in self._]

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, value):
        for one, two in zip(self, value):
            if one != two:
                return False
        return True

    def __add__(self, other: Self):
        if isinstance(other, Skip):
            return Skip()
        return Pair(self, other)

    def __radd__(self, other: Self):
        if isinstance(other, Skip):
            return Skip()
        return Pair(other, self)

    def __getitem__(self, pos: int) -> Idx:
        return self._[pos]

    def __iter__(self):
        return iter(self._)
