"""Basic operations"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from IPython.display import Math, display

from ..elements.constraint import Cons
from ..elements.element import X

if TYPE_CHECKING:
    from ..sets.functions import F
    from ..elements.variable import Var


class Func(X):
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

        # if either one or two is a number
        # set haspar to True
        if isinstance(one, (int, float)):
            self.haspar = True
            if isinstance(two, (int, float)):
                raise ValueError('Cannot multiply two numbers')
        elif isinstance(two, (int, float)):
            self.haspar = True
        else:
            self.haspar = False

        if mul and add and sub and div:
            raise ValueError('Only one operation allowed')

        if mul and isinstance(two, (int, float)):
            # keep number before the variable/operation
            # multiplications are also p*v
            one, two = two, one

        if add and isinstance(one, (int, float)):
            # keep number after the variable/operation
            # additions are always v + p
            one, two = two, one

        if sub and isinstance(one, (int, float)):
            # if negation, write as -1 * var
            if one == 0:
                # This is a negation
                one = -1
                mul = True
                sub = False
            else:
                # keep number after the variable
                # subtractions are always v - p
                one, two = two, one

        if div and two == 0:

            raise ValueError('Division by zero')

        self.one = one
        self.two = two
        self.mul = mul
        self.add = add
        self.sub = sub
        self.div = div

        super().__init__(parent=parent, pos=pos)

        # self.name = f'{self.one or ""} {self.rel} {self.two or ""}'
        self.name = ''.join([str(i) for i in self._])

    def __setattr__(self, name, value):
        # change any number to float
        if name in ['one', 'two']:

            if isinstance(value, (int, float)):
                value = float(value)

        super().__setattr__(name, value)

    def elms(self):
        """Elements (Variables and Parameters) of the function"""
        return sum(
            [i.elms() if isinstance(i, Func) else [i] for i in [self.one, self.two]],
            [],
        )

    def rels(self):
        """Relations between variables"""
        rels = []
        if isinstance(self.one, Func):
            rels += self.one.rels()

        rels += [self.rel]

        if isinstance(self.two, Func):
            rels += self.two.rels()
        return rels

    @property
    def _(self):
        """The function as a list"""
        x = []
        for n, e in enumerate(self.elms()):
            if n > 0:
                x.append(self.rels()[n - 1])
            x.append(e)

        if x[0] is None:
            x = x[1:]
        else:
            x = ['+'] + x
        return x

    def b(self, zero: bool = False) -> int | float | None:
        """Parameter
        Args:
            zero (bool, optional): returns 0 instead of None. Defaults to False.
        """

        if isinstance(self._[-1], float):
            if self._[-2] == '+':
                return -self._[-1]
            if self._[-2] == '-':
                return self._[-1]
        if zero:
            return 0

    def a(self) -> list[float]:
        """Variable coefficient vector"""
        x = self._
        if isinstance(self._[-1], float) and self._[-2] in ['+', '-']:
            # if there is a parameter in the end, that goes to the b matrix
            x = x[:-2]

        # here you get a list of tuples (rel, variable)
        x = list(zip(x[::2], x[1::2]))

        a_ = []

        for n, i in enumerate(x):
            if isinstance(i[1], float):
                # if multiplication by float
                if i[0] == '×':
                    a_[n - 1] = a_[n - 1] * i[1]
            else:
                if i[0] == '+':
                    a_.append(1.0)
                if i[0] == '-':
                    a_.append(-1.0)
        return a_

    def x(self) -> list[int]:
        """Structure of the function
        given as a list of number tags (n) for the variables (x)
        """
        x = self._
        if isinstance(self._[-1], float) and self._[-2] in ['+', '-']:
            x = x[:-2]
        x: list[Var] = x[1::2]
        return [i.n for i in x if not isinstance(i, float)]

    def latex(self) -> str:
        """Equation"""
        if self.one:
            if isinstance(self.one, (int, float)):
                one = self.one
            else:
                one = self.one.latex()
        else:
            one = ''

        if self.two:
            if isinstance(self.two, (int, float)):
                two = self.two

            else:
                two = self.two.latex()
        else:
            two = ''

        if self.rel == '+':
            return rf'{one} + {two}'

        if self.rel == '-':
            return rf'{one} - {two}'

        if self.rel == '×':
            return rf'{one} \cdot {two}'

        if self.rel == '÷':
            return rf'\frac{{{one}}}{{{two}}}'

    def matrix(self) -> tuple[list[float], int | float | None]:
        """Matrix representation"""
        return self.a(), self.b()

    def pprint(self) -> Math:
        """Display the function"""
        display(Math(self.latex()))

    def __neg__(self):
        return Func(one=0, sub=True, two=self)

    def __pos__(self):
        return self

    # the choice of how to deal with the operation is determined by the following
    # in order:

    # 1. what is the type of the other element
    # number -int, float
    # operation - Func
    # variable - Var

    # 2. whether self has a parameter or not
    # if haspar
    # if self is add, sub, mul

    # 3. if the other is an Func and has a parameter
    # there are of type Func(Func(v, p) Func(v, p))

    def __add__(self, other: int | float | Var | Self):
        # the number element is always taken at number two
        if isinstance(other, (int, float)):
            if self.haspar:
                if self.add:
                    # v + p + p1 = v + (p + p1)
                    return Func(one=self.one, add=True, two=self.two + other)
                if self.sub:
                    # v - p + p1  = v + (- p + p1)
                    if self.two > other:
                        return Func(one=self.one, sub=True, two=self.two - other)
                    return Func(one=self.one, add=True, two=other - self.two)

        if isinstance(other, Func):

            if self.haspar:
                if other.haspar:
                    if self.add:
                        if other.add:
                            # v + p + v1 + p1 = (v + v1) + (p + p1)
                            return Func(
                                one=self.one + other.one,
                                add=True,
                                two=self.two + other.two,
                            )

                        if other.sub:
                            # v + p + v1 - p1 = (v + v1) + (p - p1)
                            if self.two > other.two:
                                return Func(
                                    one=self.one + other.one,
                                    add=True,
                                    two=self.two - other.two,
                                )
                            return Func(
                                one=self.one + other.one,
                                add=True,
                                two=other.two - self.two,
                            )
                        if other.mul:
                            # v + p + p1*v = v + p1*v + p
                            return Func(one=self.one + other, add=True, two=self.two)

                    if self.sub:
                        if other.add:
                            # v - p + v1 + p1 = (v + v1) + (p + p1)
                            if self.two > other.two:
                                return Func(
                                    one=self.one + other.one,
                                    add=True,
                                    two=self.two - other.two,
                                )
                            return Func(
                                one=self.one + other.one, add=True, two=other - self.two
                            )

                        if other.sub:
                            # v - p + v1 - p1 = (v + v1) - (p + p1)
                            return Func(
                                one=self.one + other.one,
                                sub=True,
                                two=self.two + other.two,
                            )

                        if other.mul:
                            # v - p + p1*v = v + p1*v - p
                            return Func(
                                one=self.one + other.two, sub=True, two=self.two
                            )

                    if self.mul:

                        if other.add:
                            # p*v + v1 + p1 = (p*v + v1) + p1
                            return Func(one=self + other.one, add=True, two=other.two)

                        if other.sub:
                            # p*v + v1 - p1 = (p*v + v1) - p1
                            return Func(one=self + other.one, sub=True, two=other.two)

                # if the other opn has no parameter

                if self.add:
                    # v + p + v1 + v2 = (v + v1 + v2) + p
                    # v + p + v1 - v2 = (v + v1 - v2) + p
                    return Func(one=self.one + other, add=True, two=self.two)

                if self.sub:
                    # v - p + v1 + v2 = (v + v1 + v2) - p
                    # v - p + v1 - v2 = (v + v1 - v2) - p
                    # v - p + v1*v2 = (v + v1*v2) - p
                    return Func(one=self.one + other, sub=True, two=self.two)

        # if not Func or float should be Var
        if self.haspar:
            if self.add:
                # v + p + v1 = v + v1 + p)
                return Func(one=self.one + other, add=True, two=self.two)
            if self.sub:
                # v - p + v1 = v + v1 -p
                return Func(one=self.one + other, sub=True, two=self.two)

        # p*v + p1*v1 = (p*v) + p1*v1
        # v + p*v = (v) + p*v
        # p*v + v1
        # if no parameter in self
        # v1 + v2  + v3
        # v1 - v2  + v3
        # v1*v2 + v3
        return Func(one=self, add=True, two=other)

    def __radd__(self, other: float):

        if other == 0:
            return self

        return self + other

    def __sub__(self, other: float | Var | Self):

        if isinstance(other, (int, float)):
            if self.haspar:
                if self.sub:
                    # v - p - p1 = v + (p + p1)
                    return Func(one=self.one, sub=True, two=self.two + other)

                if self.add:
                    # v + p - p1  = v +  (p - p1)
                    if self.two > other:
                        return Func(one=self.one, add=True, two=self.two - other)
                    return Func(one=self.one, sub=True, two=other - self.two)

        if isinstance(other, Func):
            if self.haspar:
                if other.haspar:
                    if self.add:
                        if other.add:
                            # v + p - (v1 + p1) = (v - v1) + (p - p1)
                            if self.two > other.two:
                                return Func(
                                    one=self.one + other.one,
                                    add=True,
                                    two=self.two - other.two,
                                )
                            return Func(
                                one=self.one - other.one,
                                sub=True,
                                two=other.two - self.two,
                            )

                        if other.sub:
                            # v + p - (v1 - p1) = (v - v1) + (p + p1)
                            return Func(
                                one=self.one - other.one,
                                add=True,
                                two=self.two + other.two,
                            )

                        if other.mul:
                            # v + p + p1*v = v + p1*v + p
                            return Func(one=self.one - other, add=True, two=self.two)

                    if self.sub:
                        if other.add:
                            # v - p - (v1 + p1) = (v + v1) - (p + p1)
                            return Func(
                                one=self.one + other.one, sub=True, two=other + self.two
                            )

                        if other.sub:
                            # v - p - (v1 - p1) = (v - v1) - p + p1
                            if self.two > other.two:
                                return Func(
                                    one=self.one - other.one,
                                    sub=True,
                                    two=self.two - other.two,
                                )
                            return Func(
                                one=self.one - other.one,
                                add=True,
                                two=other.two - self.two,
                            )

                        if other.mul:
                            # v - p + p1*v = v + p1*v - p
                            return Func(
                                one=self.one - other.two, sub=True, two=self.two
                            )

                    if self.mul:

                        if other.add:
                            # p*v - (v1 + p1) = (p*v - v1) - p1
                            return Func(one=self - other.one, sub=True, two=other.two)

                        if other.sub:
                            # p*v - (v1 - p1) = (p*v - v1) + p1
                            return Func(one=self - other.one, sub=True, two=other.two)

                # if the other opn has no parameter

                if self.add:
                    # v + p + v1 + v2 = (v + v1 + v2) + p
                    # v + p + v1 - v2 = (v + v1 - v2) + p
                    return Func(one=self.one - other, add=True, two=self.two)

                if self.sub:
                    # v - p + v1 + v2 = (v + v1 + v2) - p
                    # v - p + v1 - v2 = (v + v1 - v2) - p
                    # v - p + v1*v2 = (v + v1*v2) - p
                    return Func(one=self.one - other, sub=True, two=self.two)

        # if not Func or float should be Var
        if self.haspar:
            if self.add:
                # v + p - v1 = v - v1 + p
                return Func(one=self.one - other, add=True, two=self.two)
            if self.sub:
                # v - p - v1 = v - v1 -p
                return Func(one=self.one - other, sub=True, two=self.two)

        # p*v + p1*v1 = (p*v) + p1*v1
        # v + p*v = (v) + p*v
        # p*v + v1
        # if no parameter in self
        # v1 + v2  + v3
        # v1 - v2  + v3
        # v1*v2 + v3
        return Func(one=self, sub=True, two=other)

    def __rsub__(self, other: float | Var | Self):
        if other == 0:
            return -self
        else:
            return -self + other

    def __mul__(self, other: float | Var | Self):

        if isinstance(other, (int, float)):
            if self.haspar:
                if self.add:
                    # (v + p)*p1 = v*p1 + p*p1)
                    return Func(one=self.one * other, add=True, two=self.two * other)

                if self.sub:
                    # (v - p)*p1 = v*p1 - p*p1)
                    return Func(one=self.one * other, sub=True, two=self.two * other)

                if self.mul:
                    # (p*v)*p1 = p*p1*v
                    return Func(one=self.one * other, mul=True, two=self.two)

            if self.add:
                # (v1+ v2)*p
                return Func(one=other * self.one, add=True, two=other * self.two)

            if self.sub:
                # (v1 - v2)*p
                return Func(one=other * self.one, sub=True, two=other * self.two)

            if self.mul:
                # (v1*v2)*p = p * (v1*v2)
                return Func(one=other, mul=True, two=self)

        if isinstance(other, Func):
            if self.haspar:
                if other.haspar:
                    if self.add:
                        if other.add:
                            # (v1 + p1)*(v2 + p2) = v1*v2 + v1*p2 + p1*v2 + p1*p2
                            return Func(
                                one=self.one * other.one
                                + self.one * other.two
                                + other.one * self.two,
                                add=True,
                                two=self.two * other.two,
                            )

                        if other.sub:
                            # (v1 + p1)*(v2 - p2) = v1*v2 + v1*p2 - p1*v2 - p1*p2
                            return Func(
                                one=self.one * other.one
                                - self.one * other.two
                                - other.one * self.two,
                                sub=True,
                                two=self.two * other.two,
                            )

                        if other.mul:
                            # (v1 + p1)*(p2*v2) = v1*p2*v2 + p1*p2*v2
                            return Func(
                                one=other.one * self.one * other.two,
                                add=True,
                                two=other.one * self.one * self.two,
                            )

                    if self.sub:
                        if other.add:
                            # (v1 - p1)*(v2 + p2) = v1*v2 + v1*p2 - p1*v2 - p1*p2
                            return Func(
                                one=self.one * other.one
                                + other.two * self.one
                                - self.two * other.one,
                                sub=True,
                                two=self.two * other.two,
                            )

                        if other.sub:
                            # (v1 - p1)*(v2 - p2) = v1*v2 + v1*p2 - p1*v2 - p1*p2
                            return Func(
                                one=self.one * other.one
                                + other.two * self.one
                                - self.two * other.two,
                                sub=True,
                                two=self.two * other.two,
                            )

                        if other.mul:
                            # (v1 - p1)*(p2*v2) = v1*p2*v2 - p1*p2*v2
                            return Func(
                                one=other.one * self.one * other.two,
                                sub=True,
                                two=other.two * self.two * other.two,
                            )

                    if self.mul:
                        if other.add:
                            # (p1*v1)*(v2 + p2) = p1*v1*v2 + p1*v1*p2
                            return Func(
                                one=self.one * self.two * other.two,
                                add=True,
                                two=self.one * other.one * self.two,
                            )

                        if other.sub:
                            # (p1*v1)*(v2 - p2) = p1*v1*v2 - p1*v1*p2
                            return Func(
                                one=self.one * self.two * other.two,
                                sub=True,
                                two=self.one * other.one * self.two,
                            )

                        if other.mul:
                            # (p1*v1)*(p2*v2) = p1*p2*v1*v2
                            return Func(
                                one=self.one * other.one,
                                mul=True,
                                two=self.two * other.two,
                            )

                # if the other opn has no parameter

                if self.add:
                    if other.add:
                        # (v + p)*(v1 + v2) = v*v1 + v*v2 + p*v1 + p*v2
                        return Func(
                            one=self.one * other, add=True, two=self.two * other
                        )
                    if other.sub:
                        # (v + p)*(v1 - v2) = v*v1 - v*v2 + p*v1 - p*v2
                        return Func(
                            one=self.one * other, sub=True, two=self.two * other
                        )

                    if other.mul:
                        # (v + p)*(p1*v) = v*p1*v + p*p1*v
                        return Func(
                            one=self.one * other.two, add=True, two=self.two * other.two
                        )

                if self.sub:
                    if other.add:
                        # (v - p)*(v1 + v2) = v*v1 + v*v2 - p*v1 - p*v2
                        return Func(
                            one=self.one * other, sub=True, two=self.two * other
                        )

                    if other.sub:
                        # (v - p)*(v1 - v2) = v*v1 - v*v2 - p*v1 + p*v2
                        return Func(
                            one=self.one * other, sub=True, two=self.two * other
                        )

                    if other.mul:
                        # (v - p)*(p1*v) = v*p1*v - p*p1*v
                        return Func(
                            one=self.one * other, sub=True, two=self.two * other
                        )

                if self.mul:
                    if other.add:
                        # (p*v)*(v1 + v2) = p*v*v1 + p*v*v2
                        return Func(
                            one=self * other.one, add=True, two=self * other.two
                        )

            if self.add:
                if other.add:
                    # (v1 + v2)*(v3 + v4) = v1*v3 + v1*v4 + v2*v3 + v2*v4
                    return Func(one=self.one * other, add=True, two=self.two * other)
                if other.sub:
                    # (v1 + v2)*(v3 - v4) = v1*v3  + v2*v3 - v1*v4 - v2*v4
                    return Func(one=self.one * other, sub=True, two=self.two * other)

                if other.mul:
                    # (v1 + v2)*(p*v) = v1*p*v + v2*p*v
                    return Func(
                        one=self.one * other.two, add=True, two=self.two * other.two
                    )

            if self.sub:
                if other.add:
                    # (v1 - v2)*(v3 + v4) = v1*(v3 + v4) - v2*(v3 + v4)
                    return Func(one=self.one * other, sub=True, two=self.two * other)

                if other.sub:
                    # (v1 - v2)*(v3 - v4) = v1*(v3 - v4) - v2*(v3 - v4)
                    return Func(one=self.one * other, sub=True, two=self.two * other)

                if other.mul:
                    # (v1 - v2)*(p*v) = p+v*v1 - p*v*v2
                    return Func(one=other * self.one, sub=True, two=other * self.two)

            if self.mul:
                if other.add:
                    # (p*v)*(v1 + v2) = p*v*v1 + p*v*v2
                    return Func(one=self * other.one, add=True, two=self * other.two)

                if other.sub:
                    # (p*v)*(v1 - v2) = p*v*v1 - p*v*v2
                    return Func(one=self * other.one, sub=True, two=self * other.two)

                if other.mul:
                    # (p*v)*(p1*v1) = p*p1*v*v1
                    return Func(
                        one=self.one * other.one, mul=True, two=self.two * other.two
                    )

        if self.add:
            # (v + p)*v1 = v*v1 + p*v1
            return Func(one=self.one * other, add=True, two=self.two * other)

        if self.sub:
            # (v - p)*v1 = v*v1 - p*v1
            return Func(one=self.one * other, sub=True, two=self.two * other)

        if self.mul:
            # (p*v)*v1 = p*v*v1
            return Func(one=self.one, mul=True, two=self.two * other)

        return Func(one=self, mul=True, two=other)

    def __rmul__(self, other: float | Var | Self):
        if isinstance(other, (int, float)):
            if other == 1:
                return self
            return self * other

    def __truediv__(self, other: float | Var | Self):
        return Func(one=self, div=True, two=other)

    def __eq__(self, other: float | Var | Self):
        return Cons(func=self - other)

    def __le__(self, other: float | Var | Self):
        return Cons(func=self - other, leq=True)

    def __ge__(self, other: float | Var | Self):
        return Cons(func=-self + other, leq=True)

    def __lt__(self, other: float | Var | Self):
        return self <= other

    def __gt__(self, other: float | Var | Self):
        return self >= other
