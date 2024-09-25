"""BigM 
"""

from __future__ import annotations

from typing import Self

from sympy import IndexedBase


class M:
    """BigM, infinity basically"""

    def __init__(self, _: float = None, pos: bool = True):
        # big value if needed
        self._ = _
        self.pos = pos

    @property
    def name(self):
        """name"""
        return '-M' if not self.pos or self._ < 0 else 'M'

    @property
    def sym(self):
        """Symbol"""
        return -IndexedBase('M') if not self.pos or self._ < 0 else IndexedBase('M')

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __len__(self):
        return 1

    def __neg__(self):
        return M()

    def __pos__(self):
        return M()

    def __add__(self, other: Self | float):

        if isinstance(other, M):
            if self._ and other._:
                return M(_=self._ + other._)
            else:
                return M()

        if isinstance(other, (int, float)):
            if self.pos:
                return M()
            else:
                return M(pos=False)

    def __sub__(self, other: Self):

        if isinstance(other, M):
            if self._ and other._:
                return M(_=self._ - other._)
            else:
                return -M()

        if isinstance(other, (int, float)):
            if self.pos:
                return M()
            else:
                return M(pos=False)

    def __gt__(self, other: Self):
        if isinstance(other, (int, float)):
            if self.pos:
                return True
            else:
                return False

    def __ge__(self, other: Self):
        return self > other

    def __lt__(self, other: Self):
        return not self > other

    def __le__(self, other: Self):
        return not self > other

    def __eq__(self, other: Self):

        if isinstance(other, (int, float)):
            return False

        if isinstance(other, M):
            if self._ and other._:
                if self._ == other._:
                    return True
                else:
                    return False

    def __ne__(self, other: Self):
        return not self == other
