"""Objective Function"""

from __future__ import annotations

from typing import TYPE_CHECKING

from IPython.display import Math, display

if TYPE_CHECKING:
    from .function import F


class O:
    """Objective Function"""

    def __init__(self, function: F):

        if all([v.parent is None for v in function.variables]):
            # if the function is defined using a variable element
            self.function = function[0]
            # the A matrix becomes the C matrix

            self.C = self.function.A

        else:
            # if the function is defined using variable sets
            self.function = function
            # the A matrix becomes the C matrix
            self.C = self.function.A[0]

        self.C = self.C[0] if isinstance(self.C[0], list) else self.C
        self._ = self.function

        # The index is taken from the function
        self.index = self.function.index
        # so are the variables

        self.variables = self.function.variables
        # the name, always minimization in gana
        self.name = rf'min({self.function})'
        # whats contained in the set

        # value obtained after optimization
        self.X: float = None

        # number in the program
        self.n = None

        # name given by user in program
        self.pname: str = None

    def update_variables(self):
        """Informs that the variables are optimized by this objective."""
        for v in self.variables:
            v.min_by.append(self)

    @property
    def P(self):
        """Variable positions"""
        return [v.n for v in self.variables]

    @property
    def matrix(self) -> dict:
        """Matrix as dict"""
        return self.function.matrix

    def sol(self, asfloat: bool = False):
        """Solution"""
        if asfloat:
            return self.X

        display(Math(self.latex() + r'=' + rf'{self.X}'))

    def latex(self):
        """Latex representation"""
        return rf'min \hspace{{0.2cm}} {self.function.latex()}'

    def show(self):
        """Pretty Print"""
        display(Math(self.latex()))

    def mps(self):
        """Name in MPS file"""
        return f'O{self.n}'

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))
