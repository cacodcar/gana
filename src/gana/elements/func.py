"""Basic operations"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from IPython.display import Math, display

from .cons import Cons

if TYPE_CHECKING:
    from ..sets.function import F
    from .var import Var


class Func:
    """A Mathematical Operation

    Operations are only betweeen two elements, one and two
    and have a rel betwen them, mul, add, sub, div

    elements can be a number (int, float), a variable (Var) or another operation (Func)

    In the base form of an Func haspar is True

    add (v + p)
    sub (v - p)
    mul (p*v)

    the placement of parameters (float, int) is consistent
    add/sub after the variable, mul before the variable

    Generally, if haspar is False operations can be:

    add (v1 + v2) or (opn + opn) or (v1 + opn) or (opn + v1)
    sub (v1 - v2) or (opn - opn) or (v1 - opn) or (opn - v1)
    mul (v1*v2) or (opn*opn) or (v1*opn) or (opn*v1)

    An Func cannot be defined but is rather generated when operating on:
    variables or constants or operations themselves
    """

    def __init__(
        self,
        one: float | Var | Self = 0,
        two: float | Var | Self = 0,
        mul: bool = False,
        add: bool = False,
        sub: bool = False,
        div: bool = False,
        parent: F | Cons | Var = None,
        pos: int = None,
    ):

        self.one = one
        self.two = two
        self.mul = mul
        self.add = add
        self.sub = sub
        self.div = div

        self.parent = parent
        self.pos = pos
        self.n = None

        if mul:
            self.rel = '×'
        elif add:
            self.rel = '+'
        elif sub:
            self.rel = '-'
        elif div:
            self.rel = '÷'
        else:
            raise ValueError('one of mul, add, sub or div must be True')

        self.array = sum(
            [i.array if isinstance(i, Func) else [i] for i in [self.one, self.two]],
            [],
        )

        self.vars = [i for i in self.array if not isinstance(i, (int, float))]

        self.rels = []
        if isinstance(self.one, Func):
            self.rels += self.one.rels

        self.rels += [self.rel]

        if isinstance(self.two, Func):
            self.rels += self.two.rels

        self.elms = []
        for n, e in enumerate(self.array):
            if n > 0:
                self.elms.append(self.rels[n - 1])
            self.elms.append(e)

        if self.elms[0] is None:
            self.elms = self.elms[1:]
        else:
            if isinstance(self.elms[0], (float, int)) and self.elms[0] < 0:
                self.elms = ['-', -self.elms[0]] + self.elms[1:]
            else:
                self.elms = ['+'] + self.elms

        self.name = ''.join([str(i) for i in self.elms])

    @property
    def _(self):
        """Value of the function"""
        return self.eval()

    def eval(self, one: int | float = None, two: int | float = None):
        """Evaluate the function"""

        if one is None and self.one:
            if isinstance(self.one, Func):
                one_ = self.one.eval()
            elif isinstance(self.one, (int, float)):
                one_ = self.one
            else:
                one_ = self.one._
        else:
            one_ = one

        if two is None and self.two:
            if isinstance(self.two, Func):
                two_ = self.two.eval()
            elif isinstance(self.two, (int, float)):
                two_ = self.two
            else:
                two_ = self.two._
        else:
            two_ = two

        if self.mul:
            if not one_:
                one_ = 1
            if not two_:
                two_ = 1
            return one_ * two_
        if self.div:
            return one_ / two_
        if self.add:
            if not one_:
                one_ = 0
            if not two_:
                two_ = 0
            return one_ + two_
        if self.sub:
            if not one_:
                one_ = 0
            if not two_:
                two_ = 0
            return one_ - two_


    def B(self, zero: bool = False) -> int | float | None:
        """Parameter
        Args:
            zero (bool, optional): returns 0 instead of None. Defaults to False.
        """

        if isinstance(self.elms[-1], float):
            if self.elms[-2] == '+':
                return -self.elms[-1]
            if self.elms[-2] == '-':
                return self.elms[-1]
        if zero:
            return 0

    def A(self) -> list[float]:
        """Variable coefficient vector"""
        x = self.elms
        if isinstance(self.elms[-1], float) and self.elms[-2] in ['+', '-']:
            # if there is a parameter in the end, that goes to the b matrix
            x = x[:-2]

        # here you get a list of tuples (rel, variable)
        x = list(zip(x[::2], x[1::2]))

        a_ = []

        for i in x:
            if isinstance(i[1], float):
                # if multiplication by float
                if i[0] == '+':
                    a_.append(i[1])
                if i[0] == '-':
                    a_.append(-i[1])
            elif i[1] is None:
                continue
            elif isinstance(i[1], int) and i[1] == 0:
                a_.append(0.0)
            else:
                if i[0] == '+':
                    a_.append(1.0)
                if i[0] == '-':
                    a_.append(-1.0)
        return a_

    def X(self) -> list[int]:
        """Structure of the function
        given as a list of number tags (n) for the variables (x)
        """
        x = self.elms
        if isinstance(self.elms[-1], float) and self.elms[-2] in ['+', '-']:
            x = x[:-2]
        x: list[Var] = x[1::2]
        return [i.n for i in x if i and not isinstance(i, (float, int))]

    def latex(self) -> str:
        """Equation"""
        if self.one is not None:
            if isinstance(self.one, (int, float)):
                one = self.one
            else:
                one = self.one.latex()
        else:
            one = ''

        if self.two is not None:
            if isinstance(self.two, (int, float)):
                two = self.two

            else:
                two = self.two.latex()
        else:
            two = ''

        if self.add:
            return rf'{one} + {two}'

        if self.sub:
            return rf'{one} - {two}'

        if self.mul:
            # handling negation case,
            if isinstance(one, (int, float)) and float(one) == -1.0:
                return rf'-{two}'
            return rf'{one} \cdot {two}'

        if self.div:
            return rf'\frac{{{one}}}{{{two}}}'

    def matrix(self) -> tuple[list[float], int | float | None]:
        """Matrix representation"""
        return self.A(), self.B()

    def pprint(self):
        """Display the function"""
        display(Math(self.latex()))

    def isnnvar(self):
        """Is this a neg variable"""
        if (
            isinstance(self.one, (int, float))
            and self.one in [-1, -1.0]
            and self.mul
            and not isinstance(self.two, Func)
        ):
            return True

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))
