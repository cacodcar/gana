"""Zero"""

from typing import Self


class Z:
    """Zero, Shunya"""

    def __init__(self, _: float = 0, neg: bool = False):
        """Store a nonnegative tolerance and the independent symbolic sign."""
        if _ and _ < 0:
            _error_message = "Zero value cant be negative, give neg = True"
            raise ValueError(_error_message)
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
        try:
            return hash(self.name)
        except AttributeError:
            # Fallback for uninitialized state during unpickling
            return id(self)

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
        """Reject division by symbolic zero with the established exception."""
        _error_message = "Cant divide by zero"
        raise ValueError(_error_message)

    def __gt__(self, other: Self | float):
        """Preserve signed-zero ordering and None for unordered operands.

        Gana historically orders negative signed zero above positive zero.
        NaN and unsupported operands return None rather than False.
        """
        if isinstance(other, Z):
            return bool(self.neg and not other.neg)
        if isinstance(other, (int, float)):
            if other < 0:
                return True
            if other >= 0:
                return False
        return None

    def __ge__(self, other: Self | float):
        return self > other

    def __lt__(self, other: Self | float):
        return not self > other

    def __le__(self, other: Self | float):
        return not self > other

    def __eq__(self, other: object):
        """Compare symbolic sign for zeros; other objects are unequal."""
        if isinstance(other, Z):
            if self.neg and other.neg:
                return True

            if not self.neg and not other.neg:
                return True

            if (not self.neg and other.neg) or (self.neg and not other.neg):
                return False
        else:
            return False
        return None

    def __ne__(self, other: object):
        """Return the complement of symbolic equality for any operand."""
        return not self == other

    # def __call__(self) -> IndexedBase:
    #     """Symbol"""
    #     return -IndexedBase('δ') if self.neg else IndexedBase('δ')
