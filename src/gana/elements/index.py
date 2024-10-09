"""An index"""

from typing import Self

from .element import X


class Idx(X):
    """An index"""

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __len__(self):
        return 1

    def __eq__(self, other: Self):
        if isinstance(other, Idx):
            return self.name == other.name
        return self.name == other

    def __mul__(self, other: Self):
        if isinstance(other, Idx):
            if sorted(set(self.parent) | (other.parent)) != sorted(
                self.parent + other.parent
            ):
                raise ValueError(
                    f'{other} can only belong at one index of element.',
                    f'{other} also in {self}',
                )
        print(other)
        if other == 1:
            return self

        return NotImplemented
