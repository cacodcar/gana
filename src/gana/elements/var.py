"""Variable"""

from __future__ import annotations

from typing import TYPE_CHECKING

from IPython.display import Math, display

from .cons import Cons


if TYPE_CHECKING:
    from ..sets.variable import V


class Var:
    """A variable"""

    def __init__(
        self,
        parent: V,
        pos: int,
        itg: bool = False,
        nn: bool = True,
        bnr: bool = False,
    ):

        # if the variable is an integer variable
        self.itg = itg
        # if the variable is binary
        self.bnr = bnr
        # if the variable is non negative
        self.nn = nn

        # the value taken by the variable
        self._ = None

        self.parent = parent
        self.pos = pos
        self.n = None

        # in what constraints the variable appears
        self.features: list[Cons] = []

    @property
    def name(self):
        """name of the element"""
        return f'{self.parent}_{self.pos}'

    def latex(self):
        """Latex representation"""

        name, sup = self.parent.nsplit()
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

    def sol(self):
        """Solution"""
        display(Math(self.latex() + r'=' + rf'{self._}'))

    def mps(self):
        """Name in MPS file"""
        if self.bnr:
            return f'X{self.n}'
        return f'V{self.n}'

    def vars(self):
        """Self"""
        return [self]

    def isnnvar(self):
        """Is nnvar"""
        return self.nn

    def isfix(self):
        """Is fixed"""
        if self._:
            return True

    def __rmul__(self, other: int):
        # useful when using prod()
        if isinstance(other, int) and other == 1:
            return self

    def __radd__(self, other: int):
        # useful when using sum()
        if isinstance(other, int) and other == 0:
            return self

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))
