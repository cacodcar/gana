"""A set of index elements (X)"""

from itertools import product
from typing import Self

from IPython.display import Math, display
from pyomo.environ import Set as PyoSet
from sympy import FiniteSet

from ..elements.idx import X, Skip, Idx


class I:
    """An Index Set of Elements

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

    def __init__(self, *members: tuple[str | int], size: int = None, tag: str = None):
        # if the single element is an integer
        # leave it so, it will be handled in the Program
        # has only unique members
        self.tag = tag

        if members and size:
            raise ValueError(
                'An index set can either be defined by members or size, not both'
            )

        if size:
            # make an ordered set of some size
            self._ = [X(name=i, parent=self, ordered=True) for i in range(size)]
            self.ordered = True
        else:
            self.ordered = False

        if members:
            self._ = []
            for n, i in enumerate(members):
                if isinstance(i, X):
                    self._.append(i.update(self, n))
                elif isinstance(i, Skip):
                    self._.append(Skip())
                else:
                    self._.append(X(name=i, parent=self, pos=n))
            # # This is an unordered set, has string elements
            # self._ = [
            #     (
            #         X(name=i, parent=self, pos=n)
            #         if not isinstance(i, (X, Skip))
            #         else i.update(self, n)
            #     )
            #     for n, i in enumerate(members)
            # ]

        # can be overwritten by program
        self.name = ''
        # number of the index set in the program
        self.n = None

    def step(self, i: int) -> list[X]:
        """Step up or down the index set"""
        ret = I(
            *[
                self[n + i] if n + i >= 0 and n + i <= len(self) else Skip()
                for n in range(len(self))
            ]
        )
        ret.name = f'{self.name}{i}'
        return ret

    def nsplit(self):
        """Split the name"""
        if '_' in self.name:
            name, sup = self.name.split('_')
            return name, r'^{' + sup + r'}'
        return self.name, ''

    def latex(self, descriptive: bool = True, int_not: bool = False) -> str:
        """LaTeX representation
        Args:
            descriptive (bool): print members of the index set
            int_not (bool): Whether to display the set in integer notation.

        """
        name, sup = self.nsplit()

        if descriptive:
            if self.ordered:
                if int_not:
                    return (
                        r'\{ i = '
                        + r'\mathbb{'
                        + name
                        + sup
                        + r'}'
                        + r'\mid'
                        + rf'{self._[0]}'
                        + r'\leq i \leq '
                        + rf'{self._[-1]}'
                        + r'\}'
                    )
                if len(self) < 5:
                    return (
                        r'\mathcal{'
                        + name
                        + sup
                        + r'}'
                        + r'='
                        + r'\{'
                        + r', '.join(str(x) for x in self._)
                        + r'\}'
                    )

                return (
                    r'\mathcal{'
                    + name
                    + sup
                    + r'}'
                    + r'='
                    + r'\{'
                    + rf'{self._[0]}'
                    + r',..,'
                    + rf'{self._[-1]}'
                    + r'\}'
                )
            return (
                r'\mathcal{'
                + name
                + sup
                + r'}'
                + r'='
                + r'\{'
                + r', '.join(str(x) for x in self._)
                + r'\}'
            )

        return r'\mathcal{' + str(self) + r'}'

    def pprint(self, descriptive: bool = True):
        """Display the set"""
        display(Math(self.latex(descriptive)))

    def sympy(self) -> FiniteSet:
        """Sympy representation"""
        return FiniteSet(*[str(s) for s in self._])

    def pyomo(self) -> PyoSet:
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

    def __contains__(self, other: X):
        return True if other in self._ else False

    # Avoid running instance checks
    def __eq__(self, other: Self):
        return self.name == str(other)

    def __and__(self, other: Self):
        new = []
        for i in self._:
            if i in other._:
                new.append(i)
        return I(*new)

    def __or__(self, other: Self):
        new = [i for i in self._]
        for i in other._:
            if not i in new:
                new.append(i)
        return I(*new)

    def __xor__(self, other: Self):
        new = []
        for i in self._:
            if not i in other._:
                new.append(i)
        for i in other._:
            if not i in self._:
                new.append(i)
        return I(*new)

    def __sub__(self, other: Self | int):

        if isinstance(other, I):
            return I(*[i for i in self._ if not i in other._])

        if isinstance(other, int):
            return self.step(-other)

    def __add__(self, other: int | Self):

        if isinstance(other, int):
            return self.step(other)
        i = I()
        if isinstance(other, (X, Idx, Skip)):
            i._ = [i + j for i, j in product(self._, [other])]
        else:
            lself = len(self)
            lother = len(other)

            if not lself % lother == 0 and not lother % lself == 0:
                raise ValueError(f'{self}, {other}: indices are not compatible')

            elif lself > lother:
                self_ = self._
                other_ = [x for x in other._ for _ in range(int(lself / lother))]

            elif lother > lself:
                self_ = [x for x in self._ for _ in range(int(lother / lself))]
                other_ = other._
            else:
                self_ = self._
                other_ = other._

            i._ = [i + j for i, j in zip(self_, other_)]
        i.name = rf'{[self, other]}'
        return i

    def __mul__(self, other: Self | Idx | X):
        i = I()
        if isinstance(other, (X, Idx, Skip)):
            i._ = [i & j for i, j in product(self._, [other])]
        else:
            i._ = [i & j for i, j in product(self._, other._)]
        i.name = rf'{(self, other)}'
        return i

    def __rmul__(self, other: Self):
        # this to allow using math.prod
        # in V and P for single Indices
        # makes X into Idx
        i = I()
        if isinstance(other, int) and other == 1:
            i._ = [i & None for i in self._]
            i.name = rf'{(self)}'
            return i
        # will not give error if I and I
        # safe to say that other is not I but X, Idx, or Skip
        i._ = [i & j for i, j in product([other], self._)]
        i.name = rf'{(other, self)}'
        return i

    def __iter__(self):
        return iter(self._)

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))
