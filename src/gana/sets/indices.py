"""A collection of objects, a set basically"""

from __future__ import annotations

from itertools import product
from typing import TYPE_CHECKING, Any, Self

from IPython.display import Math, display
from pyomo.environ import Set as PyoSet
from sympy import FiniteSet

from ..elements.index import Idx
from .ordered import Set

if TYPE_CHECKING:
    from ..block.program import Prg


class I(Set):
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

    def __init__(self, *indices: str):
        # if the single element is an integer
        # leave it so, it will be handled in the Program
        # has only unique members

        self.indices = indices
        self.ordered: bool = None
        super().__init__(*indices)

        self.name = 'I'

    def process(self):
        """Process the set"""
        if not self._:
            if all([isinstance(x, str) for x in self.indices]):
                self._ = [
                    Idx(name=x, parent=self, pos=n)
                    for n, x in enumerate(list(self.indices))
                ]

            elif all([isinstance(x, int) for x in self.indices]):
                self._ = [
                    Idx(name=rf'{self.name}_{n}', parent=self, pos=n)
                    for n in range(sum(self.indices))
                ]

            else:
                self._ = list(self.indices)

    def matrix(self):
        """Matrix Representation"""

    def latex(self, descriptive: bool = False) -> str:
        """LaTeX representation"""

        if descriptive:
            return (
                r'\mathcal{'
                + str(self)
                + r'}'
                + r'\in'
                + r'\{'
                + r', '.join(str(x) for x in self._)
                + r'\}'
            )

        else:
            return r'\mathcal{' + str(self) + r'}'

    def pprint(self, descriptive: bool = False) -> Math:
        """Display the set"""
        display(Math(self.latex(descriptive)))

    def sympy(self) -> FiniteSet:
        """Sympy representation"""
        return FiniteSet(*[str(s) for s in self._])

    def pyomo(self) -> Set:
        """Pyomo representation"""
        return PyoSet(initialize=[i.name for i in self._], doc=str(self))

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

    def __getitem__(self, key: int | str):
        return self._[key]

    def __contains__(self, other: Any):
        return True if other in self._ else False

    def __eq__(self, other: Self):
        if hasattr(other, '_'):
            return set(self._) == set(other._)
        return False

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

        if isinstance(other, Idx):
            if self in other.parent:
                raise ValueError(
                    f'{other} can only belong at one index of element.',
                    f'{other} also in {self}',
                )

            idxset = I(*list(product(self._, [other])))

        if isinstance(other, I):
            if set(self._) & set(other._):
                raise ValueError(
                    f'{self} and {other} have common elements',
                    f'{set(self._) & set(other._)} in both',
                )
        idxset = I(*list(product(self._, other._)))
        idxset.process()
        return idxset

    def __rmul__(self, other: Self):
        # this to allow using product
        if isinstance(other, int) and other == 1:

            return self
        if isinstance(other, Idx):
            if self in other.parent:
                raise ValueError(
                    f'{other} can only belong at one index of element.',
                    f'{other} also in {self}',
                )
            return I(*list(product([other], self._)))

        if isinstance(other, I):
            if set(self._) & set(other._):
                raise ValueError(
                    f'{self} and {other} have common elements',
                    f'{set(self._) & set(other._)} in both',
                )
        return I(*list(product(other._, self._)))

    def __iter__(self):
        return iter(self._)
