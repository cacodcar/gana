"""A Thing of an Index Set"""

from __future__ import annotations


class X:
    """A thing in the index set"""

    def __init__(self, *parents):
        self.parents = list(parents)
        self.name: str = None
        self.number: int = None

    @property
    def tag(self) -> str:
        """Unique tag for the thing"""
        return f'x{self.number}'

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __len__(self):
        return 1

    def __eq__(self, other: X):
        if isinstance(other, str):
            return self.name == other
        return self.name == other.name

    def __mul__(self, other: X):
        if isinstance(other, X):
            if self in other.parents:
                raise ValueError(
                    f'{other} can only belong at one index of element.',
                    f'{other} also in {self}',
                )
        if isinstance(other, int) and other == 1:
            return self
        return (self, other)

    def __rmul__(self, other: X):
        if isinstance(other, X):
            if self in other.parents:
                raise ValueError(
                    f'{other} can only belong at one index of element.',
                    f'{other} also in {self}',
                )
        if isinstance(other, int) and other == 1:
            return self

        return other * self
