"""A set of objects"""

from operator import is_
from typing import Any, Self

from sympy import FiniteSet


class S:
    """A Set

    Attributes:
        args (Any): Memebers of the Set
        name (str): Name of the Set
        members (set): Members of the Set. Generated from args

    Examples:
        >>> p = Program()
        >>> p.s1 = S('a', 'b', 'c')
        >>> p.s2 = S('a', 'd', 'e', 'f')

        >>> p.s1 & p.s2
        S('a')

        >>> p.s1 | p.s2
        S('a', 'b', 'c', 'd', 'e', 'f')

        >>> p.s1 ^ p.s2
        S('b', 'c', 'd', 'e', 'f')

        >>> p.s1 - p.s2
        S('b', 'c')

    """

    def __init__(self, *args: str | float, name: str = 'set'):
        self.members = list(args)
        self.name = name
        # keeps a count of, updated in program
        self.count: int = None

    @property
    def sym(self) -> FiniteSet:
        """symbolic representation"""
        return FiniteSet(*self.members)

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __len__(self):
        return len(self.members)

    def __getitem__(self, key: int | str):
        return self.members[key]

    def __contains__(self, other: Any):
        return True if other in self.members else False

    def __eq__(self, other: Self):
        if isinstance(other, S):
            if set(self.members) == set(other.members):
                return True
            else:
                return False
        else:
            return False

    def __and__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self.members) & set(other.members)))

    def __iand__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self.members) & set(other.members)))

    def __rand__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self.members) & set(other.members)))

    def __or__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self.members) | set(other.members)))

    def __ior__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self.members) | set(other.members)))

    def __ror__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self.members) | set(other.members)))

    def __xor__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self.members) ^ set(other.members)))

    def __ixor__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self.members) ^ set(other.members)))

    def __rxor__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self.members) ^ set(other.members)))

    def __sub__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self.members) - set(other.members)))

    def __isub__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self.members) - set(other.members)))

    def __rsub__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self.members) - set(other.members)))

    def __iter__(self):
        return iter(self.members)
