"""Basic operations"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from IPython.display import Math, display

from ..elements.constraint import Cons
from ..elements.element import X

if TYPE_CHECKING:
    from ..sets.functions import F
    from ..elements.variable import Var


class Opn(X):
    """A operation"""

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
            one, two = two, one

        if add and isinstance(one, (int, float)):
            # keep number after the variable/operatio
            one, two = two, one

        if sub and isinstance(one, (int, float)):

            if one == 0:
                # This is a negation
                one = -1
                mul = True
                sub = False
            else:
                # keep number after the variable
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

        if name in ['one', 'two']:

            if isinstance(value, (int, float)):
                value = float(value)

        super().__setattr__(name, value)

    # we deal with the following forms of a function at the basic level
    # note that func can just be a var
    # I None +- func
    # II par +- func
    # III func +- par
    # IV func +- func
    # V par . func
    # VI func . par
    # VII func . func

    def elms(self):
        """Elements (Variables and Parameters) of the function"""
        return sum(
            [i.elms() if isinstance(i, Opn) else [i] for i in [self.one, self.two]],
            [],
        )

    def rels(self):
        """Relations between variables"""
        rels = []
        if isinstance(self.one, Opn):
            rels += self.one.rels()

        rels += [self.rel]

        if isinstance(self.two, Opn):
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
        return Opn(one=0, sub=True, two=self)

    def __pos__(self):
        return self

    def __add__(self, other: float | Var | Self):
        # the number element is always taken at number two

        if isinstance(other, (int, float)):
            if self.haspar:
                if self.add:
                    # v + p + p1 = v + (p + p1)
                    return Opn(one=self.one, add=True, two=self.two + other)
                if self.sub:
                    # v - p + p1  = v + (- p + p1)
                    if self.two > other:
                        return Opn(one=self.one, sub=True, two=self.two - other)
                    return Opn(one=self.one, add=True, two=other - self.two)

        if isinstance(other, Opn):

            if self.haspar:
                if other.haspar:
                    if self.add:
                        if other.add:
                            # v + p + v1 + p1 = (v + v1) + (p + p1)
                            return Opn(
                                one=self.one + other.one,
                                add=True,
                                two=self.two + other.two,
                            )

                        if other.sub:
                            # v + p + v1 - p1 = (v + v1) + (p - p1)
                            if self.two > other.two:
                                return Opn(
                                    one=self.one + other.one,
                                    add=True,
                                    two=self.two - other.two,
                                )
                            return Opn(
                                one=self.one + other.one,
                                add=True,
                                two=other.two - self.two,
                            )
                        if other.mul:
                            # v + p + p1*v = v + p1*v + p
                            return Opn(one=self.one + other, add=True, two=self.two)

                    if self.sub:
                        if other.add:
                            # v - p + v1 + p1 = (v + v1) + (p + p1)
                            if self.two > other.two:
                                return Opn(
                                    one=self.one + other.one,
                                    add=True,
                                    two=self.two - other.two,
                                )
                            return Opn(
                                one=self.one + other.one, add=True, two=other - self.two
                            )

                        if other.sub:
                            # v - p + v1 - p1 = (v + v1) - (p + p1)
                            return Opn(
                                one=self.one + other.one,
                                sub=True,
                                two=self.two + other.two,
                            )

                        if other.mul:
                            # v - p + p1*v = v + p1*v - p
                            return Opn(one=self.one + other.two, sub=True, two=self.two)

                    if self.mul:

                        if other.add:
                            # p*v + v1 + p1 = (p*v + v1) + p1
                            return Opn(one=self + other.one, add=True, two=other.two)

                        if other.sub:
                            # p*v + v1 - p1 = (p*v + v1) - p1
                            return Opn(one=self + other.one, sub=True, two=other.two)

                # if the other opn has no parameter

                if self.add:
                    # v + p + v1 + v2 = (v + v1 + v2) + p
                    # v + p + v1 - v2 = (v + v1 - v2) + p
                    return Opn(one=self.one + other, add=True, two=self.two)

                if self.sub:
                    # v - p + v1 + v2 = (v + v1 + v2) - p
                    # v - p + v1 - v2 = (v + v1 - v2) - p
                    # v - p + v1*v2 = (v + v1*v2) - p
                    return Opn(one=self.one + other, sub=True, two=self.two)

        # if not Opn or float should be Var
        if self.haspar:
            if self.add:
                # v + p + v1 = v + v1 + p)
                return Opn(one=self.one + other, add=True, two=self.two)
            if self.sub:
                # v - p + v1 = v + v1 -p
                return Opn(one=self.one + other, sub=True, two=self.two)

        # p*v + p1*v1 = (p*v) + p1*v1
        # v + p*v = (v) + p*v
        # p*v + v1
        # if no parameter in self
        # v1 + v2  + v3
        # v1 - v2  + v3
        # v1*v2 + v3
        return Opn(one=self, add=True, two=other)

    def __radd__(self, other: float):

        if other == 0:
            return self

        return self + other

    def __sub__(self, other: float | Var | Self):

        if isinstance(other, (int, float)):
            if self.haspar:
                if self.sub:
                    # v - p - p1 = v + (p + p1)
                    return Opn(one=self.one, sub=True, two=self.two + other)

                if self.add:
                    # v + p - p1  = v +  (p - p1)
                    if self.two > other:
                        return Opn(one=self.one, add=True, two=self.two - other)
                    return Opn(one=self.one, sub=True, two=other - self.two)

        if isinstance(other, Opn):
            if self.haspar:
                if other.haspar:
                    if self.add:
                        if other.add:
                            # v + p - (v1 + p1) = (v - v1) + (p - p1)
                            if self.two > other.two:
                                return Opn(
                                    one=self.one + other.one,
                                    add=True,
                                    two=self.two - other.two,
                                )
                            return Opn(
                                one=self.one - other.one,
                                sub=True,
                                two=other.two - self.two,
                            )

                        if other.sub:
                            # v + p - (v1 - p1) = (v - v1) + (p + p1)
                            return Opn(
                                one=self.one - other.one,
                                add=True,
                                two=self.two + other.two,
                            )

                        if other.mul:
                            # v + p + p1*v = v + p1*v + p
                            return Opn(one=self.one - other, add=True, two=self.two)

                    if self.sub:
                        if other.add:
                            # v - p - (v1 + p1) = (v + v1) - (p + p1)
                            return Opn(
                                one=self.one + other.one, sub=True, two=other + self.two
                            )

                        if other.sub:
                            # v - p - (v1 - p1) = (v - v1) - p + p1
                            if self.two > other.two:
                                return Opn(
                                    one=self.one - other.one,
                                    sub=True,
                                    two=self.two - other.two,
                                )
                            return Opn(
                                one=self.one - other.one,
                                add=True,
                                two=other.two - self.two,
                            )

                        if other.mul:
                            # v - p + p1*v = v + p1*v - p
                            return Opn(one=self.one - other.two, sub=True, two=self.two)

                    if self.mul:

                        if other.add:
                            # p*v - (v1 + p1) = (p*v - v1) - p1
                            return Opn(one=self - other.one, sub=True, two=other.two)

                        if other.sub:
                            # p*v - (v1 - p1) = (p*v - v1) + p1
                            return Opn(one=self - other.one, sub=True, two=other.two)

                # if the other opn has no parameter

                if self.add:
                    # v + p + v1 + v2 = (v + v1 + v2) + p
                    # v + p + v1 - v2 = (v + v1 - v2) + p
                    return Opn(one=self.one - other, add=True, two=self.two)

                if self.sub:
                    # v - p + v1 + v2 = (v + v1 + v2) - p
                    # v - p + v1 - v2 = (v + v1 - v2) - p
                    # v - p + v1*v2 = (v + v1*v2) - p
                    return Opn(one=self.one - other, sub=True, two=self.two)

        # if not Opn or float should be Var
        if self.haspar:
            if self.add:
                # v + p - v1 = v - v1 + p
                return Opn(one=self.one - other, add=True, two=self.two)
            if self.sub:
                # v - p - v1 = v - v1 -p
                return Opn(one=self.one - other, sub=True, two=self.two)

        # p*v + p1*v1 = (p*v) + p1*v1
        # v + p*v = (v) + p*v
        # p*v + v1
        # if no parameter in self
        # v1 + v2  + v3
        # v1 - v2  + v3
        # v1*v2 + v3
        return Opn(one=self, sub=True, two=other)

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
                    return Opn(one=self.one*other, add=True, two=self.two * other)
                
                if self.sub:
                    # (v - p)*p1 = v*p1 - p*p1)
                    return Opn(one=self.one*other, sub=True, two=self.two * other)
                
            if self.add: 
                # (v1+ v2)*p = 
                return Opn(one=other*self.one, add=True, two=other*self.two)
            
            if self.sub:
                # (v1 - v2)*p = 
                return Opn(one=other*self.one, sub=True, two=other*self.two)
            
            if self.mul:
                # (v1*v2)*p = 
                return Opn(one=other*self.one, mul=True, two=self.two)

        if isinstance(other, Opn):
            if self.haspar:
                if other.haspar:
                    if self.add:
                        if other.add:
                            # (v1 + p1)*(v2 + p2) = v1*v2 + v1*p2 + p1*v2 + p1*p2
                            return Opn(one=self.one*other.one + self.one*other.two + other.one*self.two, add=True, two=self.two*other.two)
                        
                        if other.sub:
                            # (v1 + p1)*(v2 - p2) = v1*v2 + v1*p2 - p1*v2 - p1*p2
                            return Opn(one=self.one*other.one - self.one*other.two - other.one*self.two, sub=True, two=self.two*other.two)
                        
                        if other.mul:
                            # (v1 + p1)*(p2*v2) = v1*p2*v2 + p1*p2*v2
                            return Opn(one=other.one*self.one*other.two, add=True, two=other.one*self.one*self.two)
                        
                    if self.sub:
                        if other.add:
                            # (v1 - p1)*(v2 + p2) = v1*v2 + v1*p2 - p1*v2 - p1*p2
                            return Opn(one=self.one*other.one + other.two*self.one - self.two*other.one, sub=True, two=self.two*other.two)
                        
                        if other.sub:
                            # (v1 - p1)*(v2 - p2) = v1*v2 + v1*p2 - p1*v2 - p1*p2
                            return Opn(one=self.one*other.one + other.two*self.one - self.two*other.two, sub=True, two=self.two*other.two)
                        
                        if other.mul:
                            # (v1 - p1)*(p2*v2) = v1*p2*v2 - p1*p2*v2
                            return Opn(one=other.one*self.one*other.two, sub=True, two=other.two*self.two*other.two)
                        
                    if self.mul:
                        if other.add:
                            # (p1*v1)*(v2 + p2) = p1*v1*v2 + p1*v1*p2
                            return Opn(one=self.one*self.two*other.two, add=True, two=self.one*other.one*self.two)
                        
                        if other.sub:
                            # (p1*v1)*(v2 - p2) = p1*v1*v2 - p1*v1*p2
                            return Opn(one=self.one*self.two*other.two, sub=True, two=self.one*other.one*self.two)
                        
                        if other.mul:
                            # (p1*v1)*(p2*v2) = p1*p2*v1*v2
                            return Opn(one= self.one*other.one, mul=True, two=self.two*other.two)

                # if the other opn has no parameter

                if self.add:
                    if other.add:
                        # (v + p)*(v1 + v2) = v*v1 + v*v2 + p*v1 + p*v2
                        return Opn(one=self.one*other, add=True, two=self.two*other)
                    if other.sub: 
                        # (v + p)*(v1 - v2) = v*v1 - v*v2 + p*v1 - p*v2
                        return Opn(one=self.one*other, sub=True, two=self.two*other)
                    
                    if other.mul: 
                        # (v + p)*(p1*v) = v*p1*v + p*p1*v
                        return Opn(one=self.one*other.two, add=True, two=self.two*other.two)
                    
                if self.sub:
                    if other.add: 
                        # (v - p)*(v1 + v2) = v*v1 + v*v2 - p*v1 - p*v2
                        return Opn(one=self.one*other, sub=True, two=self.two*other)
                    
                    if other.sub:
                        # (v - p)*(v1 - v2) = v*v1 - v*v2 - p*v1 + p*v2
                        return Opn(one=self.one*other, sub=True, two=self.two*other)
                    
                    if other.mul:
                        # (v - p)*(p1*v) = v*p1*v - p*p1*v
                        return Opn(one=self.one*other, sub=True, two=self.two*other)
                    
                if self.mul:
                    if other.add:
                        # (p*v)*(v1 + v2) = p*v*v1 + p*v*v2
                        return Opn(one=self.one*other, add=True, two=self.two*other)
                    #TODO
                    




        if isinstance(other, Opn):



        
        if isinstance(self.one, (int, float)):
            if other == 1:
                return self
            

        return Opn(one=self, two=other, rel='×')

    def __rmul__(self, other: float | Var | Self):
        if isinstance(other, (int, float)):
            if other == 1:
                return self
            return Opn(one=self, rel='×', two=float(other))
        return Opn(one=other, rel='×', two=self)

    def __truediv__(self, other: float | Var | Self):
        return Opn(one=self, two=other, rel='÷')

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
