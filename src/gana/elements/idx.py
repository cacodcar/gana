"""Index elements 
Skip - do not use the index
X - index element
Idx - Tuple of index elements
Pair - Multi-Index of Idx for functions 

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self, Any


if TYPE_CHECKING:
    from ..sets.index import I


class Skip:
    """Skips the generation of model element at this index"""

    def __init__(self):
        self.parent = None
        self.pos = None

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

        if not self.ordered:
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
            return self._pos
        return rf'{self.name}'

    # check only on the basis of the name
    # does this mean string and int can be compared?
    # yes?
    # so why yes? because people might want to just insert strings
    # or numbers, as opposed to program.something
    def __eq__(self, other: Self | int):
        return self.name == str(other)

    # This creates an index
    # nth hour and mth year  for example - (n,m)
    def __and__(self, other: Self):
        if isinstance(other, Skip):
            return Skip()
        return Idx(self, other)

    def __rand__(self, other: Self | int):
        if isinstance(other, Skip):
            return Skip()
        if other is None:
            return Idx(self)
        return Idx(other, self)

    # This creates a multi-index
    # for function x(n) + y(m)
    def __add__(self, other: Self):
        if isinstance(other, Skip):
            return Skip()
        return Pair(self, other)

    def __radd__(self, other: Self):
        if isinstance(other, Skip):
            return Skip()
        return Pair(other, self)

    # required only in the case of using math.prod
    # to create multi-indices easily
    def __rmul__(self, other: int):
        if isinstance(other, int) and other == 1:
            return Idx(self)

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))


class Idx:
    """A tuple of index elements (X)
    Is actually a nested pair of index elements
    Idx is associated with Var elements
    """

    def __init__(self, one: X, two: X = None):
        self.one = one
        self.two = two

        self.name = rf'{tuple(self._)}'

    def _contents(self):
        """Constituent index elements (X)"""
        if self.two:
            return [self.one, self.two]
        return [self.one]

    @property
    def _(self) -> list[X]:
        """Constituent index elements (X)"""
        return sum(
            [idx._ if isinstance(idx, Idx) else [idx] for idx in self._contents()],
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
    def order(self):
        """Order of the index"""
        return len(self._)

    @property
    def nested(self):
        """If this is a nested pair"""
        if self.order > 2:
            return True

    # Avoid, instance checks
    def __eq__(self, other: Self):
        if self.name == str(other):
            return True

    # Idx and (Idx or X) creates Idx
    def __and__(self, other: Self):
        if isinstance(other, Skip):
            return Skip()
        return Idx(self, other)

    def __rand__(self, other: Self):
        if isinstance(other, Skip):
            return Skip()

        if other is None:
            return self

        return Idx(other, self)

    # Idx + (Idx or X) creates a Mutli-Index(Pair)
    def __add__(self, other: Self | Pair):
        if isinstance(other, Skip):
            return Skip()
        return Pair(self, other)

    def __radd__(self, other: Self | Pair):
        if isinstance(other, Skip):
            return Skip()
        return Pair(other, self)

    # required only in the case of using math.prod
    def __rmul__(self, other: int):
        return self

    def __getitem__(self, pos: int) -> X:
        return self._[pos]

    def __iter__(self):
        return iter(self._)

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))


class Pair:
    """Multi-Index for functions
    A nested pair of indices (Idx)
    Pair is associated with Func elements
    """

    def __init__(self, one: Idx, two: Idx):
        self.one = one
        self.two = two

        self.name = rf'{self._}'

    @property
    def _(self) -> list[Idx]:
        """Constituent indices (Idx)"""
        return [self.one, self.two]

    # A None indicates a Skip()
    @property
    def parent(self) -> list[I]:
        """Parents of constituent indices"""
        return [idx.parent for idx in self._]

    # A None indicates a Skip()
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

    # Avoid instance checks
    def __eq__(self, other):
        return self.name == str(other)

    # Pair and (Idx or Pair or X or Skip) creates Pair
    def __add__(self, other: Self):
        return Pair(self, other)

    def __radd__(self, other: Self):
        return Pair(other, self)

    def __getitem__(self, pos: int) -> Idx:
        return self._[pos]

    def __iter__(self):
        return iter(self._)
