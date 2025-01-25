"""A set of index elements (X)"""

from itertools import product
from math import prod
from typing import Self

from IPython.display import Math, display

from ..elements.idx import Idx, Skip, X

try:
    from pyomo.environ import Set as PyoSet

    has_pyomo = True
except ImportError:
    has_pyomo = False

try:
    from sympy import FiniteSet

    has_sympy = True
except ImportError:
    has_sympy = False


class I:
    """Set of index elements (X)

    Args:
        *members (str | int, optional): Members of the Index set. Defaults to None.
        size (int, optional): Size of the Index set, creates and ordered set. Defaults to None.
        mutable (bool, optional): If the Index set is mutable. Defaults to False.
        tag (str, optional): Tag/details. Defaults to None.

    Attributes:
        _ (list[X]): Elements of the index set.
        tag (str): Tag/details.
        ordered (bool): Ordered set, True if size is given.
        name (str): Name, set by the program.
        n (int): Number id, set by the program.

    Raise:
        ValueError: If both members and size are given.
        ValueError: If indices of elements (P, V) are not compatible.

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

    def __init__(
        self,
        *members: str | int,
        size: int = None,
        mutable: bool = False,
        tag: str = None,
    ):

        self.tag = tag
        self.mutable = mutable

        if size:
            if members:
                raise ValueError(
                    'An index set can either be defined by members or size, not both'
                )
            # make an ordered set of some size
            self._ = [X(name=i, parent=self, ordered=True) for i in range(size)]
            self.ordered = True

        elif members:
            if size:
                raise ValueError(
                    'An index set can either be defined by members or size, not both'
                )

            self._ = []
            for n, i in enumerate(members):
                if isinstance(i, X):
                    self._.append(i.update(self, n))
                elif isinstance(i, Skip):
                    self._.append(i)
                else:
                    self._.append(X(name=i, parent=self, pos=n))
            self.ordered = False

        else:
            self._ = []
            self.ordered = False

        # set by program
        self.name = ''
        self.n = None

        # These are used for index arrays for function (F) sets
        self.one: I = None
        self.two: I = None

        self.parameters = []
        self.variables = []
        self.functions = []
        self.constraints = []

    def step(self, i: int) -> list[X]:
        """Step up or down the index set
        Args:
            i (int): Step size
        """
        ret = I(
            *[
                self[n + i] if n + i >= 0 and n + i <= len(self) else Skip()
                for n in range(len(self))
            ]
        )
        ret.name = f'{self.name}{i}'
        return ret

    def nsplit(self):
        """Split the name
        If there is an underscore, the name is split into name and superscript
        """
        if '_' in self.name:
            name, sup = self.name.split('_')
            if sup:
                return name, r'^{' + sup + r'}'
            return '-' + self.name[:-1], ''
        return self.name, ''

    def latex(self, descriptive: bool = True, int_not: bool = False) -> str:
        """LaTeX representation
        Args:
            descriptive (bool): print members of the index set
            int_not (bool): Whether to display the set in integer notation.
        """
        name, sup = self.nsplit()
        name = name.replace('|', r'\cup')
        mathcal = rf'\mathcal{{{name}{sup}}}'

        if descriptive:
            if self.ordered:
                if int_not:
                    return (
                        rf'\{{ i = \mathbb{{{name}{sup}}} \mid '
                        rf'{self._[0]} \leq i \leq {self._[-1]} \}}'
                    )
                members = (
                    r', '.join(str(x) for x in self._)
                    if len(self) < 5
                    else rf'{self._[0]},..,{self._[-1]}'
                )
                return rf'{mathcal} = \{{ {members} \}}'

            members = r', '.join(x.latex() for x in self._)
            return rf'{mathcal} = \{{ {members} \}}'

        return mathcal

    def isarray(self):
        """Check if the index set is an array
        i.e. if it is for a function set (F)
        """
        if self.one and self.two:
            return True

    def reduce(self):
        """Reduce the set to a single element"""
        if self.isarray():
            if len(self.one) == len(self.two):
                if self.one == self.two:
                    return self.one.reduce()
                else:
                    return self.one.reduce() + self.two.reduce()
        return self

        # return min(self.one, self.two, key=len)

    def pprint(self, descriptive: bool = True):
        """Display the set

        Args:
            descriptive (bool, optional): Displays all members in the index set. Defaults to False.
        """
        display(Math(self.latex(descriptive)))

    def sympy(self):
        """Sympy representation"""
        if has_sympy:
            return FiniteSet(*[str(s) for s in self._])
        print(
            "sympy is an optional dependency, pip install gana[all] to get optional dependencies"
        )

    def pyomo(self):
        """Pyomo representation"""
        if has_pyomo:
            return PyoSet(initialize=[i.name for i in self._], doc=str(self))
        print(
            "pyomo is an optional dependency, pip install gana[all] to get optional dependencies"
        )

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
        # return len([i for i in self._ if not isinstance(i, Skip)])

    # Avoid running instance checks
    def __eq__(self, other: Self):
        return self.name == str(other)

    def __and__(self, other: Self):
        index = I(
            *[i for i in self._ if i in other._], mutable=self.mutable or other.mutable
        )
        return index

    def __or__(self, other: Self):
        new = list(self._)
        for i in other._:
            if not i in new:
                new.append(i)
        index = I(
            *[i.name for i in new if not isinstance(i, Skip)],
            mutable=self.mutable or other.mutable,
        )
        if other.name and self.name != other.name:
            index.name = f'{self.name} | {other.name}'
        else:
            index.name = self.name
        index.ordered = self.ordered or other.ordered
        if isinstance(new[0], Idx):
            return prod((index,))
        return index

    def __xor__(self, other: Self):
        new: list[X | Idx] = []
        for i in self._:
            if not i in other._:
                new.append(i)
        for i in other._:
            if not i in self._:
                new.append(i)
        index = I(
            *[i.name for i in new if not isinstance(i, Skip)],
            mutable=self.mutable or other.mutable,
        )
        index.name = f'{self.name} ^ {other.name}'
        index.ordered = self.ordered or other.ordered
        return index

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
            # the other is I as well
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
        i.one = self
        i.two = other
        i.name = rf'{[self, other]}'
        return i

    def __radd__(self, other: Self):
        if not other:
            return self
        return self + other

    def __mul__(self, other: Self | Idx | X):
        i = I()
        i.name = (
            '('
            + self.name.replace('(', '').replace(')', '')
            + ', '
            + other.name.replace('(', '').replace(')', '')
            + ')'
        )
        if isinstance(other, I):
            i._ = [i & j for i, j in product(self._, other._)]
            return i
        elif isinstance(other, Skip):
            i._ = [Skip()] * len(self)
            return i
        # elif isinstance(other, (X, Idx)):
        i._ = [i & other for i in self._]
        return i

    def __rmul__(self, other: Self):
        # this to allow using math.prod
        # in V and P for single Indices
        # makes X into Idx
        i = I()
        if other == 1:
            i._ = [Idx(i) for i in self._ if not isinstance(i, Skip)]
            i.name = rf'{(self)}'
            return i
        # will not give error if I and I
        # other isI but X, Idx, or Skip
        i._ = [other & i for i in self._]
        i.name = rf'{(other, self)}'
        return i

    def __iter__(self):
        return iter(self._)

    def __getitem__(self, key: int | str):
        return self._[key]

    def __contains__(self, other: X | Idx):
        return True if other in self._ else False

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))
