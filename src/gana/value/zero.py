"""Zero"""

from typing import Self


class Z:
    """Zero, Shunya"""

    def __init__(self, _: float = 0, neg: bool = False):
        if _ and _ < 0:
            raise ValueError("Zero value cant be negative, give neg = True")
        # a tolerance value if needed
        self._ = _
        self.neg = neg

    @property
    def name(self):
        """name"""
        if self.neg:
            return "-0"
        else:
            return "0"

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __len__(self):
        return 1

    def __neg__(self):
        if self.neg:
            return Z()
        else:
            return Z(neg=True)

    def __pos__(self):
        return self

    def __add__(self, other: Self | float):
        return other

    def __radd__(self, other: Self | float):
        return other

    def __sub__(self, other: Self | float):
        if isinstance(other, Z):
            return self
        else:
            return -other

    def __rsub__(self, other: Self | float):
        return other

    def __mul__(self, other: Self | float):
        return self

    def __rmul__(self, other: Self | float):
        return self

    def __truediv__(self, other: Self | float):
        return self

    def __rtruediv__(self, other: Self | float):
        raise ValueError("Cant divide by zero")

    def __gt__(self, other: Self | float):

        if isinstance(other, Z):
            if self.neg and not other.neg:
                return True

            if not self.neg and other.neg:
                return False

            if self.neg and other.neg:
                return False

            if not self.neg and not other.neg:
                return False

        if isinstance(other, (int, float)):

            if other < 0:
                return True

            if other >= 0:
                return False

    def __ge__(self, other: Self | float):
        return self > other

    def __lt__(self, other: Self | float):
        return not self > other

    def __le__(self, other: Self | float):
        return not self > other

    def __eq__(self, other: Self | float):
        if isinstance(other, Z):
            if self.neg and other.neg:
                return True

            if not self.neg and not other.neg:
                return True

            if (not self.neg and other.neg) or (self.neg and not other.neg):
                return False
        else:
            return False

    def __ne__(self, other: Self | float):
        return not self == other

    # def __call__(self) -> IndexedBase:
    #     """Symbol"""
    #     return -IndexedBase('δ') if self.neg else IndexedBase('δ')
