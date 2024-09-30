"""A set of objects"""

from typing import Any, Self

from IPython.display import Math
from pyomo.environ import Set
from sympy import FiniteSet


class S:
    """A Set

    Attributes:
        args (Any): Memebers of the Set
        name (str): Name of the Set
        _ (set): members of the Set. Made into sets themselves

    Examples:
        >>> p = Program()
        >>> p.s1 = S('a', 'b', 'c')
        >>> p.s2 = S('a', 'd', 'e', 'f')

        >>> p.s1 & p.s2
        S('a')

        >>> p.s1 | p.s2
        S('a', 'b', 'c', 'd', 'e', 'f')

        >>> p.s1 ^ p.s2
        S('b', 'c', 'd', 'e', 'f')

        >>> p.s1 - p.s2
        S('b', 'c')

    """

    def __init__(self, *_: str | float, name: str = 'set'):
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
                + r', '.join(rf'{m}' for m in self._)
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
        if isinstance(other, S):
            if set(self._) == set(other._):
                return True
            else:
                return False
        else:
            return False

    def __and__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self._) & set(other._)))

    def __iand__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self._) & set(other._)))

    def __rand__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self._) & set(other._)))

    def __or__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self._) | set(other._)))

    def __ior__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self._) | set(other._)))

    def __ror__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self._) | set(other._)))

    def __xor__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self._) ^ set(other._)))

    def __ixor__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self._) ^ set(other._)))

    def __rxor__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self._) ^ set(other._)))

    def __sub__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self._) - set(other._)))

    def __isub__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self._) - set(other._)))

    def __rsub__(self, other: Self):
        if isinstance(other, S):
            return S(*list(set(self._) - set(other._)))

    def __iter__(self):
        return iter(self._)

    def __call__(self, descriptive: bool = False) -> FiniteSet:
        return Math(self.latex(descriptive))
