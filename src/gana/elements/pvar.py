"""Parametric Variable"""

from __future__ import annotations

from typing import TYPE_CHECKING

from IPython.display import Math, display

from .cons import Cons

if TYPE_CHECKING:
    from ..sets.theta import T


class PVar:
    """A parametric variable

    Can only be declared through a parameter set.

    Args:
        parent (P): Parameter set
        pos (int): Position in the set
        itg (bool, optional): If the variable is an integer variable. Defaults to False.
        nn (bool, optional): If the variable is non-negative. Defaults to True.
        bnr (bool, optional): If the variable is binary. Defaults to False.

    Attributes:
        itg (bool): If the variable is an integer variable
        bnr (bool): If the variable is binary
        nn (bool): If the variable is non-negative
        _ (float): Value of the variable
        parent (P): Parameter set
        pos (int): Position in the variable set
        n (int): Number of the variable in the program
        features (list[Cons]): Constraints in which the variable appears
    """

    def __init__(self, parent: T, pos: int, _: tuple[int | float] = None):

        if not _:
            _ = (0, 1)

        self._ = _
        self.parent = parent
        self.pos = pos
        self.n = None

        # in what constraints the variable appears
        self.features: list[Cons] = []

    @property
    def name(self) -> str:
        """Name"""
        return f"{self.parent}_{self.pos}"

    @property
    def CRa(self):
        """CRa"""
        return [[1.0], [-1.0]]

    @property
    def CRb(self):
        """CRb"""
        return [self._[1], -self._[0]]

    def latex(self):
        """Latex representation"""

        name, sup = self.parent.nsplit()
        name = r'\theta^' + r'{' + name + r'}'
        return (
            name
            + sup
            + r'_{'
            + rf'{self.parent.index[self.pos]}'.replace('(', '').replace(')', '')
            + r'}'
        )

    def pprint(self):
        """Pretty Print"""
        display(Math(self.latex()))

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)
