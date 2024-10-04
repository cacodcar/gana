"""A Thing of an Index Set"""

from __future__ import annotations


class X:
    """A thing in the index set"""

    def __init__(self, *parents):
        self.parents = list(parents)
        self.name: str = None
        self.number: int = None

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
