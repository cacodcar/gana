"""Function Set
"""

from __future__ import annotations

from functools import reduce
from typing import TYPE_CHECKING, Self

from collections import OrderedDict


from ..elements.func import Func
from ..elements.idx import Skip
from .constraint import C
from .index import I

try:
    from IPython.display import Math, display

    has_ipython = True
except ImportError:
    has_ipython = False

if TYPE_CHECKING:
    from ..elements.idx import Idx, X
    from .parameter import P
    from .theta import T
    from .variable import V


class F:
    """Provides some relational operation between parameter sets and variable sets or function sets (F) themselves.

    Not to be declared by the user directly.
    Made based on the operation between parameter sets (P or list of numbers or number) or variable sets (V) or function sets (F).

    Args:
        one (int | float | list[int | float] | P | V | T | F, optional): First element.
        two (int | float | list[int | float] | P | V | T | F, optional): Second element. Defaults to 0.
        mul (bool, optional): Multiplication. Defaults to False.
        add (bool, optional): Addition. Defaults to False.
        sub (bool, optional): Subtraction. Defaults to False.
        div (bool, optional): Division. Defaults to False.
        consistent (bool, optional): If the function is already consistent. Saves some computation. Defaults to False.

    Attributes:
        one (P | V | F): First element
        two (P | V | F): Second element
        mul (bool): Multiplication
        add (bool): Addition
        sub (bool): Subtraction
        div (bool): Division
        rel (str): Relation symbol
        name (str): Name of the function, reads out the operation
        index (I): Index of the function set
        array (list[P | T | V]): List of elements in the function
        vars (list[V]): List of variables in the function
        struct (list[P | T | V | str]): Structure of the function
        rels (list[str]): Relations in the function
        elms (list[P | V]): Elements in the function
        isnegvar (bool): If the function is -1*v (negation)
        isconsistent (bool): If the function is consistent
        n (int): Number id, set by the program
        pname (str): Name, set by the program
        elmo (dict[int, list[P | V | T | str]]): Elements in the function with relation. Also a sesame street character

    Raises:
        ValueError: If one of mul, add, sub or div is not True
    """

    def __init__(
        self,
        one: int | float | list[int | float] | P | V | T | Self = 0,
        two: int | float | list[int | float] | P | V | T | Self = 0,
        mul: bool = False,
        add: bool = False,
        sub: bool = False,
        div: bool = False,
        consistent: bool = False,
    ):

        # A basic Function is of the type
        # P*V, V + P, V - P
        # P can be a number (int or float), parameter set (P) or list[int | float]
        # for multiplication P comes before variable

        # if the function is -1*v (negation)
        self.isnegvar = False
        self.issum: V = None
        self.istheta = False
        # self._variables = False

        if not consistent:
            # make input int | float | list into P
            one, oneP = self.checkP(one, two)
            two, twoP = self.checkP(two, one)

            # make consistent
            if (add and oneP) or (mul and twoP):
                one, two = two, one
                oneP, twoP = twoP, oneP

            if sub and oneP:
                one, two = -two, one
                sub = False
                add = True
                oneP = False
                twoP = True

            consistent = True

        self.isconsistent = consistent
        # check for mismatch in length

        mis = self.mismatch(one, two)

        if mis < 1:
            # two is longer
            one_ = [x for x in one._ for _ in range(-mis)]
            two_ = two._

        elif mis > 1:
            # one is longer
            one_ = one._
            two_ = [x for x in two._ for _ in range(mis)]

        else:
            # one and two are of the same length
            one_ = one._
            two_ = two._

        self.mis = mis

        # index is a combination

        index: I = None
        if one.index:
            index += one.index
            one.index.functions.append(self)

        if two.index:
            index += two.index
            two.index.functions.append(self)

        if index:

            index.functions.append(self)

        # self.consistent()

        # These are of the type P*V, V + P, V - P
        # indices should match in these cases

        self._: list[Func] = []

        # Check for mismatched indices

        # self.idx = {}
        args = {'mul': mul, 'add': add, 'sub': sub, 'div': div}

        n = 0
        for i, j in zip(one_, two_):
            if isinstance(index[n], Skip):
                self._.append(None)
                n += 1
                continue
            self._.append(
                Func(
                    **args,
                    one=i,
                    two=j,
                    parent=self,
                    pos=n,
                )
            )
            n += 1

        self.index = index

        self.args = args
        self.one_ = one_
        self.two_ = two_

        self.mul = mul
        self.add = add
        self.sub = sub
        self.div = div

        self._one = one
        self._two = two

        if mul:
            rel = '×'
            # elems = [self]
        elif add:
            rel = '+'
            # elems = [one, two]
        elif sub:
            rel = '-'
            # elems = [one, -two]
        elif div:
            rel = '÷'
            # elems = [self]
        else:
            raise ValueError('one of mul, add, sub or div must be True')

        self.name = f'{one or ""}{rel}{two or ""}'
        self.rel = rel

        # set by program
        self.n: int = None
        self.pname: str = ''

        self.types()
        # variable coefficients
        self.A = [[] for _ in range(len(self))]
        # position of continuous variables in program
        self.X = [[] for _ in range(len(self))]
        # position of discrete variables in program
        self.Y = [[] for _ in range(len(self))]
        # position of theta variables in program
        self.Z = [[] for _ in range(len(self))]

        # rhs parameters
        self.B = [0 for _ in range(len(self))]
        # pvar (theta) parameters
        self.F = [[] for _ in range(len(self))]

        self.matrix()

        v_ = OrderedDict((i, []) for i in range(len(self)))
        v_ = {i: [] for i in range(len(self))}
        for i in range(len(self)):
            for n, e in enumerate(self.elems_):
                if self.vars[n]:
                    if e[i]:
                        v_[i].append(e[i])
                elif self.funcs[n]:
                    if e[i]:
                        v_[i].extend(e[i].variables)
        self.variables = v_

    @property
    def one(self):
        """Element one"""
        return self._one(self.index.one)

    @property
    def two(self):
        """Element two"""
        return self._two(self.index.two)

    @property
    def elems(self):
        """Elements"""
        return [self.one, self.two]

    @property
    def elems_(self):
        """Elements"""
        return [self.one_, self.two_]

    def types(self):
        """Types of the elements"""
        from .parameter import P
        from .theta import T
        from .variable import V

        self.vars = [True if isinstance(i, V) else False for i in self.elems]
        self.pars = [True if isinstance(i, P) else False for i in self.elems]
        self.funcs = [True if isinstance(i, F) else False for i in self.elems]
        self.pvars = [True if isinstance(i, T) else False for i in self.elems]

    def matrix(self):
        """Coefficient matrix"""

        if self.pars[0]:
            if self.funcs[1]:
                self.F = self.two.F
                self.Z = self.two.Z
                self.A = self.two.A
                self.X = self.two.X
                self.B = [p * b for p, b in zip(self.one.B, self.two_)]

            elif self.vars[1]:
                A = [[0] * len(self.two_) for _ in range(len(self.two_))]
                X = [[None] * len(self.two_) for _ in range(len(self.two_))]
                for n, o in enumerate(self.one_):
                    if self.two_[n] is not None:
                        # self.two_[n].func.append(self[n])
                        A[n][n] = o
                        X[n][n] = self.two_[n].n
                self.A = A
                self.X = X

            elif self.pvars[1]:
                F = [[0] * len(self.two_) for _ in range(len(self.two_))]
                Z = [[None] * len(self.two_) for _ in range(len(self.two_))]
                for n, o in enumerate(self.one_):
                    if self.two_[n] is not None:
                        F[n][n] = o
                        Z[n][n] = self.two_[n].n
                self.F = F
                self.Z = Z

        elif self.pars[1]:
            if self.funcs[0]:
                self.F = self.one.F
                self.Z = self.one.Z
                self.A = self.one.A
                self.X = self.one.X
                if self.sub:
                    self.B = [p + b for p, b in zip(self.two_, self.one.B)]
                if self.add:
                    self.B = [-p + b for p, b in zip(self.two_, self.one.B)]

            elif self.vars[0]:
                A = [[0] * len(self.two_) for _ in range(len(self.two_))]
                X = [[None] * len(self.two_) for _ in range(len(self.two_))]
                for n, o in enumerate(self.two_):
                    if self.one_[n] is not None:
                        # self.one_[n].func.append(self[n])
                        A[n][n] = 1.0
                        X[n][n] = self.one_[n].n
                self.A = A
                self.X = X
                if self.sub:
                    self.B = [p for p in self.two_]
                if self.add:
                    self.B = [-p for p in self.two_]

            elif self.pvars[0]:
                F = [[0] * len(self.one_) for _ in range(len(self.one_))]
                Z = [[None] * len(self.one_) for _ in range(len(self.one_))]
                for n, o in enumerate(self.two_):
                    if self.one_[n] is not None:
                        F[n][n] = 1.0
                        Z[n][n] = self.two_[n].n
                self.F = F
                self.Z = Z
                if self.sub:
                    self.B = [p for p in self.two_]
                if self.add:
                    self.B = [-p for p in self.two_]
        else:
            c = 0
            for e in self.elems:

                from .theta import T
                from .variable import V

                if isinstance(e, V):
                    A = [[0] * len(self.two_) for _ in range(len(self))]
                    X = [[None] * len(self.two_) for _ in range(len(self))]
                    if self.add:
                        for n, o in enumerate(self):
                            if self.elems_[c][n] is not None:
                                # e[n].func.append(self[n])
                                A[n][n] = 1.0
                                X[n][n] = self.elems_[c][n].n

                    if self.sub:
                        if c == 1:
                            for n, o in enumerate(self):
                                if self.elems_[c][n] is not None:
                                    A[n][n] = -1.0
                                    X[n][n] = self.elems_[c][n].n

                        else:
                            for n, o in enumerate(self):
                                if self.elems_[c][n] is not None:
                                    A[n][n] = 1.0
                                    X[n][n] = self.elems_[c][n].n

                    self.A = [a + b for a, b in zip(self.A, A)]
                    self.X = [a + b for a, b in zip(self.X, X)]

                elif isinstance(e, T):
                    F = [[0] * len(self) for _ in range(len(self))]
                    Z = [[None] * len(self) for _ in range(len(self))]
                    if self.add:
                        for n, o in enumerate(self):
                            if self.elems_[c][n] is not None:
                                F[n][n] = -1.0
                                Z[n][n] = self.elems_[c][n].n

                    if self.sub:
                        for n, o in enumerate(self):
                            if self.elems_[c][n] is not None:
                                F[n][n] = 1.0
                                Z[n][n] = self.elems_[c][n].n

                    self.F = [a + b for a, b in zip(self.F, F)]
                    self.Z = [a + b for a, b in zip(self.Z, Z)]

                else:
                    if self.add:
                        self.F = [a + [-i for i in b] for a, b in zip(self.F, e.F)]
                        self.Z = [a + b for a, b in zip(self.Z, e.Z)]
                        self.A = [a + b for a, b in zip(self.A, e.A)]
                        self.X = [a + b for a, b in zip(self.X, e.X)]
                        self.B = [-(a + b) for a, b in zip(self.B, e.B)]

                    elif self.sub:
                        if c == 1:
                            self.F = [a + b for a, b in zip(self.F, e.F)]
                            self.Z = [a + b for a, b in zip(self.Z, e.Z)]
                            self.A = [a + [-i for i in b] for a, b in zip(self.A, e.A)]
                            self.X = [a + b for a, b in zip(self.X, e.X)]
                            self.B = [-(a + b) for a, b in zip(self.B, e.B)]

                        else:
                            self.F = [a + [-i for i in b] for a, b in zip(self.F, e.F)]
                            self.Z = [a + b for a, b in zip(self.Z, e.Z)]
                            self.A = [a + b for a, b in zip(self.A, e.A)]
                            self.X = [a + b for a, b in zip(self.X, e.X)]
                            self.B = [-(a + b) for a, b in zip(self.B, e.B)]

                c += 1

    def checkP(self, inp: list[float] | float, other: V | F) -> tuple[P, bool]:
        """Make input into a parameter set (P)"""
        from .parameter import P

        if isinstance(inp, (int, float)):
            p = P(
                _=[
                    inp if not isinstance(other.index[_], Skip) else 0.0
                    for _ in range(len(other))
                ],
            )
            p.index = other.index
            p.name = str(inp)
            p.isnum = True
            return p, True

        elif isinstance(inp, list):
            p = P(I(size=len(inp)), _=inp)
            p.name = 'φ'  # other.name.capitalize()
            return p, True

        elif isinstance(inp, P):
            return inp, True
        return inp, False

    def checkT(self, inp: tuple[int | float], other: V | F) -> T:
        """Make input into a theta"""
        from .theta import T

        if isinstance(inp, tuple):
            t = T(other.index, _=inp)
            t.name = 'Theta'
            return t

        elif isinstance(inp, list):
            t = T(I(size=len(inp)), _=inp)
            t.name = 'θ'  # other.name.capitalize()
            return t, True

        elif isinstance(inp, T):
            return inp, True
        return inp, False

    def mismatch(self, one, two):
        """Determine mismatch between indices"""
        if one and two:
            lone = len(one)
            ltwo = len(two)

            if not lone % ltwo == 0 and not ltwo % lone == 0:
                raise ValueError('The indices are not compatible')
            if lone > ltwo:
                return int(lone / ltwo)
            if ltwo > lone:
                # negative to indicate that two is greater than one
                return -int(ltwo / lone)
        return 1

    def latex(self) -> str:
        """Equation"""

        if self.one is not None:
            # if isinstance(self.one, (int, float)):
            #     one = self.one
            # else:
            one_ = self.one(self.index.one)
            # TODO issum phantom V
            if self.funcs[0] and one_.issum:
                v, hold, over = self.one.issum
                oneissum = v.name
                one = rf'\sum_{{i \in {over}}} {oneissum}_{{{str(hold).replace('[', '').replace(']','')}, i}}'

            else:
                one = one_.latex()

        else:
            one = None

        if self.two is not None:
            # if isinstance(self.two, (int, float)):
            #     two = self.two
            # else:
            two_ = self.two(self.index.two)
            if self.funcs[1] and two_.issum:
                v, hold, over = self.two.issum
                twoissum = v.name
                two = rf'\sum_{{i \in {over}}} {twoissum}_{{{str(hold).replace('[', '').replace(']','')}, i}}'

            else:
                two = two_.latex()
        else:
            two = None

        if not two:
            return rf'{one}'

        if not one:
            return rf'{two}'

        if self.add:
            return rf'{one} + {two}'

        if self.sub:
            if self.funcs[0] and self.funcs[1]:
                if not self.one.mul and not self.two.mul:
                    return rf'({one}) - ({two})'
            return rf'{one} - {two}'

        if self.mul:
            # handling special case where something is multiplied by -1
            if self.isnegvar:
                # if self.one and self.one.isnum and self.one[0] in [-1, -1.0]:
                return rf'-{two}'
            # if isinstance(one, (int, float)) and float(one) == -1.0:
            #     return rf'-{two or ""}'

            return rf'{one or ""} \cdot {two or ""}'

        if self.div:
            return rf'\frac{{{str(one) or ""}}}{{{str(two) or ""}}}'

    def pprint(self, descriptive: bool = False):
        """Display the function"""
        if has_ipython:
            if descriptive:
                for f in self._:
                    display(Math(f.latex()))
            else:
                display(Math(self.latex()))
        else:
            print(
                'IPython is an optional dependency, pip install gana[all] to get optional dependencies'
            )

    def __neg__(self):

        if self.add:
            return F(one=-self.one, sub=True, two=self.two)

        if self.sub:
            return F(one=-self.one, add=True, two=self.two)

        if self.mul:
            return F(one=-self.one, mul=True, two=self.two)

        if self.div:
            return F(one=-self.one, div=True, two=self.two)

    def __pos__(self):
        return self

    def __add__(self, other: Self | P | V | T):
        if isinstance(other, (int, float)) and other in [0, 0.0]:
            return self
        return F(one=self, add=True, two=other)

    def __radd__(self, other: Self | P | V | int | float | T):
        if isinstance(other, (int, float)) and other in [0, 0.0]:
            return self
        if not other:
            return self
        return self + other

    def __sub__(self, other: Self | P | V | T):
        if isinstance(other, (int, float)) and other in [0, 0.0]:
            return self
        return F(one=self, sub=True, two=other)

    def __rsub__(self, other: Self | P | V | T):
        if isinstance(other, (int, float)) and other in [0, 0.0]:
            return -self
        else:
            return -self + other

    def __mul__(self, other: Self | P | V | T):
        if isinstance(other, (int, float)):
            if other in [0, 0.0]:
                return 0
            if other in [1, 1.0]:
                return self

        if self.add:
            return F(one=other * self.one, add=True, two=other * self.two)

        if self.sub:
            return F(one=other * self.one, sub=True, two=other * self.two)

        if self.mul:
            return F(one=other * self.one, mul=True, two=self.two)

        return F(one=self, mul=True, two=other)

    def __rmul__(self, other: Self | P | V | int | float | T):
        if isinstance(other, (int, float)):
            if other in [0, 0.0]:
                return 0
            if other in [1, 1.0]:
                return self

        return self * other

    def __truediv__(self, other: Self | P | V | T):
        if isinstance(other, (int, float)) and other in [1, 1.0]:
            return self

        if isinstance(other, (int, float)) and other in [0, 0.0]:
            return self
        return F(one=self, div=True, two=other)

    def __eq__(self, other: Self | P | V | T):
        return C(funcs=self - other)

    def __le__(self, other: Self | P | V | T):
        return C(funcs=self - other, leq=True)

    def __ge__(self, other: Self | P | V | T):
        return C(funcs=-self + other, leq=True)

    def __lt__(self, other: Self | P | V | T):
        return self <= other

    def __gt__(self, other: Self | P | V | T):
        return self >= other

    def __call__(self, *key: tuple[X | Idx | I]) -> Self:

        if reduce(lambda a, b: a + b, key) == self.index:
            return self

        # func = F(one=self.one())
        # par = P(tag=self.tag)
        # par.name, par.n = self.name, par.n

        # # if a subset is called
        # if isinstance(prod(key), I):
        #     par.index = prod(key)
        #     par._ = [self.idx[idx] for idx in prod(key)]
        #     return par

        # # if a single index is called
        # if len(key) == 1:
        #     key = None & key[0]
        # else:
        #     key = reduce(lambda a, b: a & b, key)
        # par.index = key
        # par._ = [self.idx[key]]
        # return par

    def __getitem__(self, pos: int) -> Func:
        return self._[pos]

    def __iter__(self):
        return iter(self._)

    def order(self) -> list:
        """order"""
        return len(self.index)

    def __len__(self):
        return len(self._)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)
