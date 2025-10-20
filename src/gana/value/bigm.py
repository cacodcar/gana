"""BigM"""

from typing import Self


class M:
    """BigM, infinity basically"""

    def __init__(self, _: float = None, neg: bool = False):

        # big value if needed
        self._ = _
        # if this is a negative big M

        self.neg = neg
        if neg:
            self.name = r"M_{-}"
        else:
            self.name = r"M"

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

    def __pos__(self):
        return self

    def __add__(self, other: Self | float):
        return self

    def __radd__(self, other: Self | float):
        return self

    def __sub__(self, other: Self):
        return self

    def __mul__(self, other: Self):
        return self

    def __rmul__(self, other: Self):
        return self

    def __truediv__(self, other: Self):
        return self

    def __rtruediv__(self, other: Self):
        return 0

    def __gt__(self, other: Self):
        if isinstance(other, (float, int)):
            return True

    def __ge__(self, other: Self):
        return self > other

    def __lt__(self, other: Self):
        return not self > other

    def __le__(self, other: Self):
        return not self > other

    def __eq__(self, other: Self):
        return False

    def __ne__(self, other: Self):
        return not self == other
