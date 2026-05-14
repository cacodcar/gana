"""Element of a Program"""

from __future__ import annotations

from itertools import product
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from .index import I
    from .variable import V as VType


class _E:
    """
    Element base class
    """

    def __init__(
        self,
        *index: I,
        tag: str = "",
        ltx: str = "",
        mutable: bool = False,
        name: str = "",
    ):
        self.tag = tag
        self._ltx = ltx
        self.mutable = mutable
        self.name = name

        from .variable import V

        # this takes any variable in the indices and sets them as [V]
        # and them creates an empty list for the rest of the indices
        if any([isinstance(i, tuple) for i in index]):
            # if index is a set of indices,
            # needs to be done for each index
            _index = []
            _map = {}
            for idx in index:
                _index.append(tuple([i if not isinstance(i, V) else [i] for i in idx]))

            # iterates over each individual index
            # and creates a mapping for it
            for idx in _index:
                for i in product(*idx):
                    _map[i] = None
            _index = set(_index)

        else:
            # if not set
            _index = tuple([i if not isinstance(i, V) else [i] for i in index])

            if _index:
                _map = {i: None for i in product(*_index)}

            else:
                _map = {}

        self.index: tuple[I, ...] | set[tuple[I, ...]] = _index
        self.map: dict[tuple[I, ...], V] = _map

        # this is the nth element of its type
        self.n: int = None
        self.parent: Self = None
        self.pos: int = None

        self._: list[Self] = []

        # this helps in the index check when calling functions
        self.elements = [self]

    # -----------------------------------------------------
    #                    Vector
    # -----------------------------------------------------

    def __iter__(self) -> Self:
        return iter(self._)

    def __getitem__(self, pos: int) -> VType:
        return self._[pos]

    def __len__(self):
        return len(self.map)

    # -----------------------------------------------------
    #                    Hashing
    # -----------------------------------------------------

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __hash__(self):
        try:
            return hash(self.name)
        except AttributeError:
            # Fallback for uninitialized state during unpickling
            return id(self)

    def __init_subclass__(cls):
        # the hashing will be inherited by the subclasses
        cls.__repr__ = _E.__repr__
        cls.__hash__ = _E.__hash__
