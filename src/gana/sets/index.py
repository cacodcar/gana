"""A collection of objects, a set basically"""

from __future__ import annotations

from typing import Any, Self, TYPE_CHECKING
from itertools import product

from IPython.display import Math
from pyomo.environ import Set
from sympy import FiniteSet

if TYPE_CHECKING:
    from ..block.program import Prg


class I:
    """An Index Set is a dimensio

    Attributes:
        args (Any): Memebers of the Set
        name (str): Name of the Set
        _ (set): members of the Set. Made into sets themselves

    Examples:
        >>> p = Program()
        >>> p.s1 = I('a', 'b', 'c')
        >>> p.s2 = I('a', 'd', 'e', 'f')

        >>> p.s1 & p.s2
        I('a')

        >>> p.s1 | p.s2
        I('a', 'b', 'c', 'd', 'e', 'f')

        >>> p.s1 ^ p.s2
        I('b', 'c', 'd', 'e', 'f')

        >>> p.s1 - p.s2
        I('b', 'c')

    """

    def __init__(self, *_: str):
        # if the single element is an integer
        # leave it so, it will be handled in the Program
        # has only unique members
        self._: list = list(_)
        # number, name will be updated in Program
        self.name: str = None
        self.number: int = None

    def latex(self, descriptive: bool = False) -> str:
        """LaTeX representation"""

        if descriptive:
            return (
                r'\mathcal{'
                + str(self)
                + r'}'
                + r'\in'
                + r'\{'
                + r', '.join(rf'{m._[0]}' for m in self._)
                + r'\}'
            )

        else:
            return r'\mathcal{' + str(self) + r'}'

    def sympy(self) -> FiniteSet:
        """Sympy representation"""
        return FiniteSet(*[str(s) for s in self._])

    def pyomo(self) -> Set:
        """Pyomo representation"""
        return Set(initialize=self._, doc=str(self))

    def mps(self, pos: int) -> str:
        """MPS representation
        Args:
            pos (int): Position of the member in the set
        """
        return rf'_{self[pos]}'.upper()

    def lp(self, pos: int) -> str:
        """LP representation
        Args:
            pos (int): Position of the member in the set
        """
        return rf'_{self[pos]}'

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __len__(self):
        return len(self._)

    def __getitem__(self, key: int | str):
        return self._[key]

    def __contains__(self, other: Any):
        return True if other in self._ else False

    def __eq__(self, other: Self):
        return set(self._) == set(other._)

    def __and__(self, other: Self):
        return I(*list(set(self._) & set(other._)))

    def __or__(self, other: Self):
        return I(*list(set(self._) | set(other._)))

    def __xor__(self, other: Self):
        return I(*list(set(self._) ^ set(other._)))

    def __sub__(self, other: Self):
        return I(*list(set(self._) - set(other._)))

    def __mul__(self, other: Self):
        # this to allow using product
        if isinstance(other, int) and other == 1:
            return self
        return I(*list(product(self._, other._)))

    def __rmul__(self, other: Self):
        return self * other

    def __iter__(self):
        return iter(self._)

    def __call__(self, descriptive: bool = False) -> FiniteSet:
        return Math(self.latex(descriptive))
