"""BigM 
"""

from typing import Self

from sympy import IndexedBase


class M:
    """BigM, infinity basically"""

    def __init__(self, _: float = None, neg: bool = False):
        if _ and _ < 0:
            raise ValueError('Big M cannot be negative, give neg = True')
        # big value if needed
        self._ = _
        # if this is a negative big M
        self.neg = neg

    @property
    def name(self):
        """name"""
        if self.neg:
            return '-M'
        else:
            return 'M'

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __len__(self):
        return 1

    def __neg__(self):
        if self.neg:
            return M()
        else:
            return M(neg=True)

    def __pos__(self):
        return self

    def __add__(self, other: Self | float):
        return self

    def __radd__(self, other: Self | float):
        return self

    def __sub__(self, other: Self):
        return self

    def __rsub__(self, other: Self):
        return -self

    def __mul__(self, other: Self):
        return self

    def __rmul__(self, other: Self):
        return self

    def __truediv__(self, other: Self):
        return self

    def __rtruediv__(self, other: Self):
        return 0

    def __gt__(self, other: Self):
        if isinstance(other, M):

            if self.neg and not other.neg:
                return True

            if not self.neg and other.neg:
                return False

            if self.neg and other.neg:
                return False

            if not self.neg and not other.neg:
                return False

        if isinstance(other, (int, float)):
            if self.neg:
                return False
            else:
                return True

    def __ge__(self, other: Self):
        return self > other

    def __lt__(self, other: Self):
        return not self > other

    def __le__(self, other: Self):
        return not self > other

    def __eq__(self, other: Self):
        if isinstance(other, M):
            if self.neg and other.neg:
                return True

            if not self.neg and not other.neg:
                return True

            if (not self.neg and other.neg) or (self.neg and not other.neg):
                return False
        else:
            return False

    def __ne__(self, other: Self):
        return not self == other

    def __call__(self) -> IndexedBase:
        return -IndexedBase('M') if self.neg else IndexedBase('M')
