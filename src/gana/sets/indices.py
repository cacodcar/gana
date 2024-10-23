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

    def __init__(self, *members: str, size: int = None, name: str = 'I'):
        # if the single element is an integer
        # leave it so, it will be handled in the Program
        # has only unique members

        ordered = False
        if all([isinstance(x, str) for x in members]):
            members = [
                Idx(name=x, parent=self, pos=n) for n, x in enumerate(list(members))
            ]

        if size:
            members = [Idx(name=f'idx{x}', parent=self, pos=x) for x in range(size)]
            ordered = True

        self.ordered = ordered
        self._: list[Idx] = members

        super().__init__(*members, name=name)

    def __setattr__(self, name, value):

        if name == 'name' and value and self.ordered:
            for m in self._:
                m.name = rf'{value}{m.pos}'

        super().__setattr__(name, value)

    def latex(self, descriptive: bool = False) -> str:
        """LaTeX representation"""

        if self.ordered:
            itr = list(range(len(self)))
        else:
            itr = self._

        if descriptive:
            return (
                r'\mathcal{'
                + str(self)
                + r'}'
                + r'\in'
                + r'\{'
                + r', '.join(str(x) for x in itr)
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

    def __len__(self):
        return len(self._)

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
            return I(*list(product(self._, [other])), name=f'{self}_{other}')

        return I(*list(product(self._, other._)), name=f'{self}_{other}')

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
            return I(*list(product([other], self._)), name=f'{self}_{other}')

        if isinstance(other, I):
            if set(self._) & set(other._):
                raise ValueError(
                    f'{self} and {other} have common elements',
                    f'{set(self._) & set(other._)} in both',
                )
        return I(*list(product(other._, self._)), name=f'{self}_{other}')

    def __iter__(self):
        return iter(self._)
