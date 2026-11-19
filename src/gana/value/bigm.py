"""BigM"""

from typing import Self


class M:
    """BigM, infinity basically"""

    def __init__(self, _: float | None = None, neg: bool = False):
        """Retain an optional finite placeholder and the symbolic sign."""

        # big value if needed
        self._ = _
        # if this is a negative big M

        self.neg = neg
        if neg:
            self.name = r"M_{-}"
        else:
            self.name = r"M"

    def __repr__(self):
        """Display the signed Big M symbol."""
        return self.name

    def __hash__(self):
        """Hash the signed name, using identity until a name is available."""
        try:
            return hash(self.name)
        except AttributeError:
            # Fallback for uninitialized state during unpickling
            return id(self)

    def __len__(self):
        """Count symbolic Big M as one scalar."""
        return 1

    def __pos__(self):
        """Preserve the signed Big M under unary plus."""
        return self

    def __add__(self, other: Self | float):
        """Return this Big M when adding an operand."""
        return self

    def __radd__(self, other: Self | float):
        """Return this Big M when adding it to a left operand."""
        return self

    def __sub__(self, other: Self):
        """Return this Big M when subtracting an operand."""
        return self

    def __mul__(self, other: Self):
        """Preserve this Big M under multiplication."""
        return self

    def __rmul__(self, other: Self):
        """Preserve this Big M when it is the right-hand factor."""
        return self

    def __truediv__(self, other: Self):
        """Preserve this Big M when it is the numerator."""
        return self

    def __rtruediv__(self, other: Self):
        """Return numerical zero when this Big M is the denominator."""
        return 0

    def __gt__(self, other: Self):
        """Exceed finite numbers; retain None for unsupported comparisons."""
        if isinstance(other, (float, int)):
            return True
        return None

    def __ge__(self, other: Self):
        """Use the same ordering as the strict greater-than comparison."""
        return self > other

    def __lt__(self, other: Self):
        """Return the logical negation of the greater-than comparison."""
        return not self > other

    def __le__(self, other: Self):
        """Use the same ordering as the less-than comparison."""
        return not self > other

    def __eq__(self, other: object):
        """Preserve symbolic infinity's non-equality with every operand."""
        return False

    def __ne__(self, other: object):
        """Return the complement of symbolic equality for any operand."""
        return not self == other
