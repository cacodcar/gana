"""A collection of objects, a set basically"""

from typing import Any, Self
from itertools import product

from IPython.display import Math
from pyomo.environ import Set
from sympy import FiniteSet


class I:
    """An Index Set

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

    def __init__(self, *_: str, name: str = 'set'):

        if len(_) == 1:
            self.is_set = False
        else:
            self.is_set = True
            if sorted(_, key=str) != sorted(set(_), key=str):
                raise ValueError('Members in Index set must be unique')

        self._ = list(_)
        self.name = name
        # keeps a count of, updated in program
        self.count: int = None

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
        if self.is_set:
            return set(self._) == set(other._)
        else:
            return self._ == other._

    def __and__(self, other: Self):
        return I(*list(set(self._) & set(other._)), name=f'{self.name}&{other.name}')

    def __or__(self, other: Self):
        return I(*list(set(self._) | set(other._)), name=f'{self.name}|{other.name}')

    def __xor__(self, other: Self):
        return I(*list(set(self._) ^ set(other._)), name=f'{self.name}^{other.name}')

    def __sub__(self, other: Self):
        return I(*list(set(self._) - set(other._)), name=f'{self.name}-{other.name}')

    def __mul__(self, other: Self):
        return I(*list(product(self._, other._)), name=f'{self.name}*{other.name}')

    def __iter__(self):
        return iter(self._)

    def __call__(self, descriptive: bool = False) -> FiniteSet:
        return Math(self.latex(descriptive))
