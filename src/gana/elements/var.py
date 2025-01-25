"""Variable"""

from __future__ import annotations

from typing import TYPE_CHECKING

from IPython.display import Math, display

from .cons import Cons

if TYPE_CHECKING:
    from ..sets.variable import V
    from .func import Func


class Var:
    """A variable

    Can only be declared through a variable set.

    Args:
        parent (V): Variable set
        pos (int): Position in the set
        itg (bool, optional): If the variable is an integer variable. Defaults to False.
        nn (bool, optional): If the variable is non-negative. Defaults to True.
        bnr (bool, optional): If the variable is binary. Defaults to False.

    Attributes:
        itg (bool): If the variable is an integer variable
        bnr (bool): If the variable is binary
        nn (bool): If the variable is non-negative
        _ (float): Value of the variable
        parent (V): Variable set
        pos (int): Position in the variable set
        n (int): Number of the variable in the program
        features (list[Cons]): Constraints in which the variable appears
    """

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

        self._name = ''
        self._name_set = False

        self.features: list[Cons] = []

    @property
    def name(self):
        """name of the element"""
        if not self._name or not self._name_set:
            if self.parent:
                self._name = f'{self.parent}_{self.pos}'
            else:
                self._name_set = False
        return self._name

    @property
    def index(self):
        """Index of the variable set"""
        return self.parent.index

    def latex(self):
        """Latex representation"""

        name, sup = self.parent.nsplit()
        return (
            name
            + sup
            + r'_{'
            + rf'{self.index[self.pos]}'.replace('(', '').replace(')', '')
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
        return self.name

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)
