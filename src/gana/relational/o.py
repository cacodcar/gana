"""Objective"""

from __future__ import annotations

from typing import TYPE_CHECKING

from IPython.display import Math

if TYPE_CHECKING:
    from .f import F


class O:
    """Minimization Objective"""

    def __init__(self, *args: tuple[F], name: str = 'min'):
        self.func: F = args[0]
        self.name = name

        # keeps a count of, updated in program
        self.count: int = None

    def latex(self) -> str:
        """Latex representation"""
        return rf'min {self.func.latex()}'

    def sympy(self):
        """Sympy representation"""
        return self.func.sympy()

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __len__(self):
        return 1

    def __call__(self):
        return Math(self.func.latex())
