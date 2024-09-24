"""For unbounded parameters
"""

from typing import Self
from sympy import IndexedBase


class M:
    """
    If big is True:
        A really big number like the weight on my shoulders
    If big is False:
        really small number like the money in my bank account

    Attributes:
        big (bool): True if big, False if small
        m (float): small m value

    """

    def __init__(self, big: bool = True, m: float = None, pos: bool = True):
        self.big = big
        self.m = m
        self.pos = pos

        if self.big:
            self.name = 'M'
        else:
            self.name = 'm'

        if not self.pos:
            self.name = '-' + self.name

    @property
    def sym(self):
        """Symbol"""
        return IndexedBase(f'{self.name}')

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __len__(self):
        return 1

    def __neg__(self):

        return M(big=True, pos=False)

    def __pos__(self):
        return M(big=True, pos=True)

    def __add__(self, other: Self | int | float):

        if isinstance(other, (M, int, float)):
            if self.pos:
                return M(big=True)
            else:
                return M(big=True, pos=False)

    def __sub__(self, other: Self):
        if isinstance(other, (M, int, float)):
            if self.pos:
                return M(big=True)
            else:
                return M(big=True, pos=False)

    def __gt__(self, other: Self):
        if isinstance(other, (int, float)):
            # BigM is always greater than any number
            return self.big
        if isinstance(other, M):
            if other.big is False:
                return self.big

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
            if self.big == other.big:
                return True
            else:
                return False

    def __ne__(self, other: Self):
        return not self == other
