"""Zero
"""

from __future__ import annotations

from typing import Self

from sympy import IndexedBase


class Z:
    """Zero, Shunya"""

    def __init__(self, _: float = None, pos: bool = True):
        # big value if needed
        self._ = _
        self.pos = pos

    @property
    def name(self):
        """name"""
        return '-zero' if not self.pos or self._ < 0 else 'zero'

    @property
    def sym(self):
        """Symbol"""
        return -IndexedBase('δ') if not self.pos or self._ < 0 else IndexedBase('δ')

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __len__(self):
        return 1

    def __neg__(self):
        return Z()

    def __pos__(self):
        return Z()

    def __add__(self, other: Self | float):
        if isinstance(other, Z):
            return Z(_=self._ + other._)

        if isinstance(other, (int, float)):
            return other

    def __sub__(self, other: Self | float):
        if isinstance(other, Z):
            return Z(_=self._ - other._)

        if isinstance(other, (int, float)):
            return -other

    def __gt__(self, other: Self | float):

        if isinstance(other, Z):
            # zero is smaller
            return self._ > other._

        if isinstance(other, (int, float)):

            if other >= 0:
                return False
            else:
                return True

    def __ge__(self, other: Self | float):

        if isinstance(other, Z):
            # zero is smaller
            return self._ >= other._

        if isinstance(other, (int, float)):
            if other >= 0:
                return False
            else:
                return True

    def __lt__(self, other: Self | float):
        return not self > other

    def __le__(self, other: Self | float):
        return not self >= other

    def __eq__(self, other: Self | float):

        if isinstance(other, Z):
            if self._ == other._:
                return True

        if isinstance(other, (int, float)):
            if other == 0:
                return True

    def __ne__(self, other: Self | float):
        return not self == other
