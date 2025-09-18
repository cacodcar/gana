"""Paramter Set"""

from __future__ import annotations

import enum
from itertools import product
from math import prod
from typing import TYPE_CHECKING, Self
from warnings import warn

from IPython.display import Math, display

from .birth import make_T
from .cases import Elem, PCase
from .function import F
from .index import I
from .variable import V

if TYPE_CHECKING:
    from .theta import T

try:
    from pyomo.environ import Param as PyoParam

    has_pyomo = True
except ImportError:
    has_pyomo = False

try:
    from sympy import Idx, IndexedBase, symbols

    has_sympy = True
except ImportError:
    has_sympy = False


class P:
    """Ordered set of parameters

    Does not support inf and nan values.

    Args:
        *index (tuple[I], optional): Indices. Defaults to None.
        _ (list[int | float], optional): list of parameters. Defaults to None.
        mutable (bool): If the parameter is mutable
        tag (str): Tag/details

    Attributes:
        index (I): Index of the parameter set.
        _ (list[int | float]): List of parameters. All converted to float.
        mutable (bool): If the parameter is mutable.
        tag (str): Tag/details.
        name (str): Name, set by the program
        n (int): Number id, set by the program.
        map (dict[X | Idx, Var]): Index to parameter mapping.
        case (PCase): Special case of a parameter set

    Raises:
        ValueError: If != operator is used with any other type (not P)
        ValueError: If the parameter values and length of indices do not match
    """

    # TODO update Errors in docstring

    def __init__(
        self,
        *index: I,
        _: list[float] | float = None,
        mutable: bool = False,
        tag: str = None,
        ltx: str = None,
    ):
        # given at declaration
        self.tag = tag
        self._ltx = ltx
        self.mutable = mutable

        # name will be set by the program later
        # if dummy index, the name is set to 'φ' (phi)
        self.name = ''

        # special case of the parameter
        self.case: PCase = PCase.SET
        # set the index
        # self.index: tuple[I] | set[tuple[I]] = index

        if any([isinstance(i, tuple) for i in index]):
            self.n_splices = len(index)
            # if index is a set of indices,
            # needs to be done for each index
            _index = []
            _map = {}
            for idx in index:
                _index.append(tuple([i if not isinstance(i, V) else [i] for i in idx]))

            # iterates over each individual index
            # and creates a mapping for it
            for idx in _index:
                for i in product(*idx):
                    _map[i] = None
            _index = set(_index)

        else:
            # number of splices of the index set
            self.n_splices = 1
            # if not set
            _index = tuple([i if not isinstance(i, V) else [i] for i in index])

            if _index:
                _map = {i: None for i in product(*_index)}

            else:
                _map = {}

        self.index: tuple[I] | set[tuple[I]] = _index
        self.map: dict[I, V] = _map

        # contains the set of parameters
        if _ is None:
            self._ = []
        else:
            self._: list[float | int] = _  # always a list of parameters

        # set by the program
        # this is the nth parameter declared
        self.n: int = None

        # this helps in the index check when calling functions
        self.elements = [self]

        if isinstance(self._, (int, float)):
            # if int or float is passed it is a single number
            # names for these are generated automatically
            # in __str__()
            self.name = str(_)  # set the name to the number
            if _ > 0:
                # postive number
                self.case = PCase.NUM
            elif _ < 0:
                # negative number
                self.case = PCase.NEGNUM
            else:
                # 0
                self.case = PCase.ZERO

            if self.index:
                # if index is passed
                # make length equal to index
                self._ = [float(_)] * len(self.map)
            else:
                self.index = (I(size=1, dummy=True),)
                self._ = [float(_)]

        else:
            # if some sort of iterable is passed
            # preferably a list
            # set by program
            if not self.index and self._:
                # if index is not passed
                # make a dummy index
                self.index = (I(size=len(self._), dummy=True),)
                # here the map needs to be remade
                self.map = {i: None for i in list(product(*self.index))}
                self.name = 'φ'  # set the name to phi
            self._ = [float(p) for p in self._]

        # fill in the values
        for n, k in enumerate(self.map):
            self.map[k] = self._[n]

        # if self._:
        #     self.create_map()

        #     # check if there is a mismatch between the length of data
        #     # and the length of index passed
        #     if len(self.map) != len(self._):
        #         raise ValueError(
        #             f"Index mismatch: len(values) ({len(self._)}) ! = len(index) ({len(self.map)})"
        #         )
        # else:
        #     self.map = {}

    @property
    def args(self) -> dict[str, str | bool]:
        """Return the arguments of the parameter set"""
        return {'tag': self.tag, 'ltx': self.ltx, 'mutable': self.mutable}

    @property
    def ltx(self) -> str:
        """LaTeX representation of the variable set"""
        if self._ltx:
            return r'{' + self._ltx + r'}'
        # if user has not set the LaTeX representation
        # the name becomes the latex representation
        if self.name:
            return r'{' + self.name.replace('_', r'\_') + r'}'
        return self._ltx

    # -----------------------------------------------------
    #                   Matrix
    # -----------------------------------------------------
    @property
    def A(self) -> list[list[float]]:
        """Generate a diagonal matrix representation of the variable set"""
        return [[self._[i]] for i in range(len(self))]

    # [
    #         [self._[i] if i == j else 0 for j in range(len(self))]
    #         for i in range(len(self))
    #     ]

    # -----------------------------------------------------
    #                    Helpers
    # -----------------------------------------------------

    # def create_map(self):
    #     """Create a map of indices to parameters"""
    #     self.map: dict[I, float | int] = {
    #         prod(i): self._[n] for n, i in enumerate(list(product(*self.index)))
    #     }

    # -----------------------------------------------------
    #                    Printing
    # -----------------------------------------------------

    def latex(self) -> str:
        """LaTeX representation"""

        if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
            return str(self)

        index = (
            r'_{'
            + rf'{self.index}'.replace('(', '')
            .replace(')', '')
            .replace('[', '{')
            .replace(']', '}')
            + r'}'
        )

        if len(self.index) == 1:
            # if there is a single index element
            # then a comma will show up in the end, replace that
            return self.ltx + index.replace(',', '')  # type: ignore

        return self.ltx + index

    def show(self, descriptive: bool = False):
        """Display the variables
        Args:
            descriptive (bool, optional): If True, shows all parameters. Defaults to False.
        """
        if descriptive:
            # just print out the parameters
            for p in self._:
                print(p)

        display(Math(self.latex()))

    # -----------------------------------------------------
    #                    Value
    # -----------------------------------------------------

    def __neg__(self):
        if self.case == PCase.ZERO:
            # if zero return self
            return self

        if self.case in [PCase.NUM, PCase.NEGNUM]:
            # if number return a negation

            return P(*self.index, _=-self._[-1])

        # else negate the number and return a new parameter set
        p = P(*self.index, _=[-i for i in self._], **self.args)
        if self.case == PCase.NEGSET:
            # if this is already a negated set
            # make it a normal set now
            p.name = f'{self.name[1:]}'  # remove the negative sign
            p.case = PCase.SET
        else:
            # if this is a normal set
            # make it a negated set
            p.case = PCase.NEGSET
            p.name = f'-{self}'  # add the negative sign
        # return the new parameter set
        return p

    def __pos__(self):

        if self.case == PCase.NEGNUM:
            # if it is a negative number
            # return a positive number
            return P(*self.index, _=-self._[-1], **self.args)

        if self.case == PCase.NEGSET:
            p = P(*self.index, _=[-i for i in self._], **self.args)
            p.name = self.name[1:]  # remove the negative sign
            return p

        # if self.case in [PCase.ZERO, PCase.SET, PCase.NUM]:
        # if it is zero, a normal set, or a number
        # return itself
        return self

    def __abs__(self):
        if self.case == PCase.ZERO:
            # if zero return self
            return self

        if self.case == PCase.SET:
            # if it is a set return a normal set
            p = P(*self.index, _=[abs(i) for i in self._], **self.args)
            p.name = f'|{self.name}|'
            return p

        if self.case in [PCase.NEGNUM, PCase.NEGSET]:
            # if it is a negative number or a negated set
            # return a positive number or a normal set
            return -self
        # else just itself
        return self

    def __float__(self):
        if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
            return self._[-1]
        return self

    # -----------------------------------------------------
    #                    Operators
    # -----------------------------------------------------
    # --- Handling basic operations----
    # if there is a zero on the left, just return P
    # if the other is a parameter, add the values
    # if the other is a function/variable, return a function

    # r<operation>
    # for the right hand side operations
    # they only kick in when the left hand side operator
    # does not have the operation/the operation did not work
    # in this case, we just do the equivalent self

    def __add__(
        self,
        other: (
            V
            | Self
            | T
            | F
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> P:
        if other is None:
            # if adding with None
            return self

        if self.case == PCase.ZERO:
            # if self is zero
            # return other
            return other

        if isinstance(other, (int, float)):
            # if adding to a number
            if other in [0, 0.0]:
                # if adding zero, return self
                return self

            if self.case in [PCase.NEGNUM, PCase.NUM]:
                # P (number) - other
                # the number will be set to NEGNUM, NUM
                if self._[-1] + other in [0, 0.0]:
                    # if number returns zero, return int 0
                    return 0

                return P(*self.index, _=self._[-1] + other, **self.args)

            # if set or negative set
            # just add the number to each value
            # and return new parameter set
            p = P(*self.index, _=[i + other for i in self._], **self.args)
            p.name = f'({self}+{other})'
            return p

        if isinstance(other, list):
            # lengths should match
            if self.case in [PCase.NUM, PCase.NEGNUM]:
                p = P(*self.index, _=[self._[-1] + i for i in other], **self.args)

            else:
                if len(self) != len(other):
                    warn(
                        f"Index mismatch {self} + {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                    )
                # if list, just zip through the values and add
                p = P(
                    *self.index, _=[i + j for i, j in zip(self._, other)], **self.args
                )
            # change the name to add that something from a list has been added
            p.name = f'({self}+φ)'
            return p

        if isinstance(other, tuple):
            # if tuple, make T
            # and make a function
            return F(
                one=make_T(other, index=self.index),
                add=True,
                two=self,
                one_type=Elem.T,
                two_type=Elem.P,
            )

        if isinstance(other, P):
            # lengths should match

            if other.case == PCase.ZERO:
                # if other is zero
                return self

            if self.case in [PCase.NUM, PCase.NEGNUM]:

                if other.case in [PCase.NUM, PCase.NEGNUM]:
                    # if both are numbers
                    # let P handle the case
                    if self._[-1] + other._[-1] in [0, 0.0]:
                        # if number returns zero, return int 0
                        return 0

                    return P(*self.index, _=self._[-1] + other._[-1], **self.args)
                # else make a new parameter set

                p = P(*self.index, _=[self._[-1] + i for i in other._], **self.args)
                p.name = f'({self}+{other})'
                return p

            if other.case in [PCase.NUM, PCase.NEGNUM]:
                # if other is a number, add other to every value in the set
                p = P(*self.index, _=[i + other._[-1] for i in self._], **self.args)
                p.name = f'({self}+{other})'
                return p

            if len(self) != len(other):
                warn(
                    f"Index mismatch {self} + {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                )
            # if either one of them is general parameter
            p = P(*self.index, _=[i + j for i, j in zip(self._, other._)], **self.args)
            p.name = f'({self}+{other})'
            return p

        # if not parameter, let the other handle elements operator handle the addition
        if self.case in [PCase.NEGNUM, PCase.NEGSET]:
            # if negative number, handle using sub, but keep parameter at two
            # (-P) + E = E - P
            return F(one=other, sub=True, two=-self, two_type=Elem.P)

        # keep additive or subtractive parameter at two
        # P + E = E + P
        return F(one=other, add=True, two=self, two_type=Elem.P)

    def __radd__(
        self,
        other: (
            V
            | Self
            | T
            | F
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> P:
        # let __add__() handle the addition
        return self + other

    def __sub__(
        self,
        other: (
            V
            | Self
            | T
            | F
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> P | F:
        if other is None:
            # if adding with None
            return self

        if self.case == PCase.ZERO:
            # if self is zero
            # return negative of other
            return -other

        if isinstance(other, (int, float)):
            # if adding to a number
            if other in [0, 0.0]:
                # if adding zero, return self
                return self

            if self.case in [PCase.NEGNUM, PCase.NUM]:

                if self._[-1] - other == 0:
                    # if number returns zero, return int 0
                    return 0

                # let P make a .NUM type
                return P(*self.index, _=self._[-1] - other, **self.args)

            p = P(*self.index, _=[i - other for i in self._], **self.args)
            p.name = f'({self}-{other})'
            return p

        if isinstance(other, list):
            # if list, just zip through the values and add

            if self.case in [PCase.NUM, PCase.NEGNUM]:
                p = P(*self.index, _=[self._[-1] - i for i in other], **self.args)
            else:
                if len(self) != len(other):
                    warn(
                        f"Index mismatch {self} - {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                    )
                p = P(
                    *self.index, _=[i - j for i, j in zip(self._, other)], **self.args
                )
                # change the name to add that something from a list has been added
            p.name = f'({self}-φ)'
            return p

        if isinstance(other, tuple):
            # if tuple, make T
            # and make a function
            return F(
                one=make_T(other, index=self.index),
                sub=True,
                two=self,
                one_type=Elem.T,
                two_type=Elem.P,
            )

        if isinstance(other, P):

            if other.case == PCase.ZERO:
                # if other is zero
                return self

            if self.case in [PCase.NUM, PCase.NEGNUM]:

                if other.case in [PCase.NUM, PCase.NEGNUM]:
                    # if both are numbers
                    # let P handle the case
                    if self._[-1] - other._[-1] in [0, 0.0]:
                        # if number returns zero, return int 0
                        return 0
                    # let P handle the case based on the value that is determines
                    return P(*self.index, _=self._[-1] - other._[-1], **self.args)

                p = P(*self.index, _=[self._[-1] - i for i in other._], **self.args)
                p.name = f'({self}-{other.name})'
                return p

            if other.case in [PCase.NUM, PCase.NEGNUM]:
                # if other is a number subtract every value in self with the number
                p = P(*self.index, _=[i - other._[-1] for i in self._], **self.args)
                p.name = f'({self}-{other})'
                return p

            if len(self) != len(other):
                raise ValueError(
                    f"Index mismatch {self} - {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                )

            # if both are just general parameters
            # zip through the values and subtract
            p = P(*self.index, _=[i - j for i, j in zip(self._, other._)], **self.args)
            p.name = f'({self}-{other})'
            return p

        # if not parameter, let the other handle elements operator handle the addition
        if self.case in [PCase.NEGNUM, PCase.NEGSET]:
            # if negative number, handle using function sub, but keep parameter at two
            # -P - E = -E - P
            return F(one=-other, sub=True, two=self, two_type=Elem.P)

        # keep additive or subtractive parameter at two
        # P - E = -E + P
        return F(one=-other, add=True, two=self, two_type=Elem.P)

    def __rsub__(
        self,
        other: (
            V
            | Self
            | T
            | F
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> P | F:
        # let negation and __add__ handle the subtraction
        return -self + other

    def __mul__(
        self,
        other: (
            V
            | Self
            | T
            | F
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> P:

        if other is None:
            # if multiplying by nothing, return nothing
            return None

        if self.case == PCase.ZERO:
            # if self is zero, return zero
            return 0

        if isinstance(other, (int, float)):
            # if multiplying with a number
            if other in [1, 1.0]:
                # by unity, return itself
                return self
            if other in [0, 0.0]:
                # by zero, return 0
                return 0.0

            if self.case in [PCase.NEGNUM, PCase.NUM]:
                # if self is a number, just find the product
                # let P handle the rest
                return P(*self.index, _=self._[-1] * other, **self.args)

            # else multiply the number to each value
            p = P(*self.index, _=[i * other for i in self._], **self.args)
            p.name = f'{self}*{other}'
            return p

        if isinstance(other, list):
            # if list, just zip through the values and multiply
            if self.case in [PCase.NUM, PCase.NEGNUM]:
                p = P(*self.index, _=[self._[-1] * i for i in other], **self.args)
            else:
                if len(self) != len(other):
                    warn(
                        f"Index mismatch {self} * {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                    )
                p = P(
                    *self.index, _=[i * j for i, j in zip(self._, other)], **self.args
                )
            p.name = f'{self}*φ'
            return p

        if isinstance(other, tuple):
            # if tuple, make T
            # return a scaled T
            if self.case == PCase.ZERO:
                # return int zero
                return 0

            if self.case in [PCase.NUM, PCase.NEGNUM]:
                # if self is a number, scale the tuple by the number
                # and make a T

                t = make_T(
                    tuple([other[0] * self._[-1], other[1] * self._[-1]]), self.index
                )
                t.name = f'{self}*θ'
                return t

            # otherwise self is a set
            # scale the tuple by each value in the set
            t = make_T(
                [tuple([i * other[0], i * other[1]]) for i in self._], self.index
            )
            t.name = f'{self}*θ'
            return t

        if isinstance(other, P):

            if other.case == PCase.ZERO:
                # if self or other is zero, return int zero
                return 0

            if self.case in [PCase.NUM, PCase.NEGNUM]:
                # if self is a number, just find the product
                # let P handle the rest
                if other.case in [PCase.NUM, PCase.NEGNUM]:

                    if other._[0] in [0, 0.0]:
                        # if other is zero, return int zero
                        return 0

                    return P(*self.index, _=self._[-1] * other._[-1], **self.args)

                p = P(*self.index, _=[self._[-1] * i for i in other._], **self.args)
                p.name = f'{self}*{other}'
                return p

            if other.case in [PCase.NUM, PCase.NEGNUM]:
                # if other is a number, find the product of every value in self with the number
                p = P(*self.index, _=[i * other._[-1] for i in self._], **self.args)
                p.name = f'{self}*{other}'
                return p

            if len(self) != len(other):
                raise ValueError(
                    f"Index mismatch {self} * {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                )
            # if both are just general parameters
            # else zip through the values and multiply
            p = P(*self.index, _=[i * j for i, j in zip(self._, other._)], **self.args)
            p.name = rf"{self}*{other}"
            return p

        return other * self
        # TODO - handle multiplication with other types
        # call multiplication function
        # if isinstance(other, F):
        #     # if other is a function, use it
        #     # let F handle the multiplication
        #     if other.add:
        #         # if the function is an addition, return a function
        #         if self.case in [PCase.NEGNUM, PCase.NEGSET]:
        #             if other.two_type == Elem.P:
        #                 # if the other is a parameter, make it a subtraction
        #                 return F(one=self * other.one, sub=True, two=self * other.two)
        #             # make it a subtraction
        #             return F(one=self * other.one, sub=True, two=self * other.two)

        #         return F(one=self * other.one, add=True, two=self * other.two)

        # return F(one=self, mul=True, two=other, one_type=Elem.P)

    def __rmul__(
        self,
        other: (
            V
            | Self
            | T
            | F
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> P:
        # multiplication is commutative
        return self * other

    def __truediv__(
        self,
        other: (
            V
            | Self
            | T
            | F
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> P:
        try:
            if other is None:
                # if dividing by nothing, return nothing
                raise ValueError(
                    "Cannot divide by None. Please provide a valid parameter, variable, or number."
                )

            if self.case == PCase.ZERO:
                # if self is zero, return zero
                # take every opportunity to return int 0
                return 0

            if isinstance(other, (int, float)):
                # if dividing by a number
                if other in [0, 0.0]:
                    # if dividing by zero, raise an error
                    raise ZeroDivisionError(f'{self} cannot be divided by zero.')

                if other in [1, 1.0]:
                    return self

                if self.case in [PCase.NEGNUM, PCase.NUM]:
                    # if self is a number, just find the division
                    # let P handle the rest
                    return P(*self.index, _=self._[-1] / other, **self.args)

                p = P(*self.index, _=[i / other for i in self._], **self.args)
                p.name = f'{self}/{other}'
                return p

            if isinstance(other, list):
                if isinstance(other[0], tuple):
                    raise ValueError(
                        "Cannot divide by a list of tuples. Please provide a valid parameter, variable, or number."
                    )

                if self.case in [PCase.NUM, PCase.NEGNUM]:
                    # if self is a number, divide the number by each value in the list
                    p = P(*self.index, _=[self._[-1] / i for i in other], **self.args)

                else:
                    if len(self) != len(other):
                        warn(
                            f"Index mismatch {self} / {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                        )
                    # if list, just zip through the values and divide
                    p = P(
                        *self.index,
                        _=[i / j for i, j in zip(self._, other)],
                        **self.args,
                    )
                    # change the name to add that something from a list has been added
                    p.name = f'{self}/φ'
                    return p

            if isinstance(other, tuple):
                # dividing by parametric variable
                raise ValueError(
                    f"Cannot divide {self} by a tuple. Please provide a valid parameter, variable, or number."
                )

            if isinstance(other, P):

                if other.case == PCase.ZERO:
                    raise ZeroDivisionError(f'{self} cannot be divided by zero.')

                if self.case in [PCase.NEGNUM, PCase.NUM]:
                    if other.case in [PCase.NUM, PCase.NEGNUM]:
                        # if both are numbers
                        # let P handle the case
                        return P(*self.index, _=self._[-1] / other._[-1], **self.args)

                    p = P(*self.index, _=[self._[-1] / i for i in other._], **self.args)
                    p.name = f'{self}/{other}'
                    return p

                if other.case in [PCase.NUM, PCase.NEGNUM]:
                    # if other is a number, divide every value in self by the number
                    p = P(*self.index, _=[i / other._[-1] for i in self._], **self.args)
                    p.name = f'{self}/{other}'
                    return p

                if len(self) != len(other):
                    raise ValueError(
                        f"Index mismatch {self} / {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                    )
                # if both are just general parameters
                # zip through the values and divide
                p = P(*self.index, _=[i / j for i, j in zip(self._, other._)])
                p.name = f'{self}/{other}'
                return p

            # P / E: not handled yet
            raise ValueError(
                f"Cannot divide {self} by {other}. Nonlinear operations are not supported for {type(other).__name__} objects."
            )

        except ZeroDivisionError as e:
            # handle division by zero
            raise ZeroDivisionError(f'{self} cannot be divided by zero.') from e

    def __rtruediv__(
        self,
        other: (
            V
            | Self
            | T
            | F
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> P:
        # just do this operation instead
        return (1 / self) * other

    def __floordiv__(
        self,
        other: (
            V
            | Self
            | T
            | F
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> P:
        if other is None:
            # if dividing by nothing, return nothing
            raise ValueError(
                "Cannot divide by None. Please provide a valid parameter, variable, or number."
            )

        if self.case == PCase.ZERO:
            # if self is zero, return zero
            return 0

        if isinstance(other, (int, float)):
            # if dividing by a number
            if other in [0, 0.0]:
                # if dividing by zero, raise an error
                raise ZeroDivisionError(f'{self} cannot be divided by zero.')

            if other in [1, 1.0]:
                return self

            if self.case in [PCase.NEGNUM, PCase.NUM]:
                # if self is a number, just find the division
                # let P handle the rest
                return P(*self.index, _=self._[-1] // other, **self.args)

            p = P(*self.index, _=[i // other for i in self._], **self.args)
            p.name = f'{self}//{other}'
            return p

        if isinstance(other, list):
            if isinstance(other[0], tuple):
                raise ValueError(
                    "Cannot divide by a list of tuples. Please provide a valid parameter, variable, or number."
                )

            if self.case in [PCase.NUM, PCase.NEGNUM]:
                p = P(*self.index, _=[self._[-1] // i for i in other], **self.args)
            else:
                if len(self) != len(other):
                    warn(
                        f"Index mismatch {self} // {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                    )
                # if list, just zip through the values and divide
                p = P(
                    *self.index, _=[i // j for i, j in zip(self._, other)], **self.args
                )
            # change the name to add that something from a list has been added
            p.name = f'{self}//φ'
            return p

        if isinstance(other, tuple):
            # dividing by parametric variable
            raise ValueError(
                f"Cannot divide {self} by a tuple. Please provide a valid parameter, variable, or number."
            )

        if isinstance(other, P):

            if other.case == PCase.ZERO:
                raise ZeroDivisionError(f'{self} cannot be divided by zero.')

            if self.case in [PCase.NEGNUM, PCase.NUM]:
                if other.case in [PCase.NUM, PCase.NEGNUM]:
                    # if both are numbers
                    # let P handle the case
                    return P(*self.index, _=self._[-1] // other._[-1], **self.args)

                p = P(*self.index, _=[self._[-1] // i for i in other._], **self.args)
                p.name = f'{self}//{other}'
                return p
            if other.case in [PCase.NUM, PCase.NEGNUM]:
                # if other is a number, divide every value in self by the number
                p = P(*self.index, _=[i // other._[-1] for i in self._], **self.args)
                p.name = f'{self}//{other}'
                return p
            if len(self) != len(other):
                raise ValueError(
                    f"Index mismatch {self} // {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                )
            # if both are just general parameters
            # zip through the values and divide
            p = P(*self.index, _=[i // j for i, j in zip(self._, other._)], **self.args)
            p.name = f'{self}//{other}'
            return p

        # else let the other handle the division
        return self // other

    def __mod__(
        self,
        other: (
            V
            | Self
            | T
            | F
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> P:
        if other is None:
            # if dividing by nothing, return nothing
            raise ValueError(
                "Cannot divide by None. Please provide a valid parameter, variable, or number."
            )
        if self.case == PCase.ZERO:
            # if self is zero, return zero
            return 0

        if isinstance(other, (int, float)):
            # if dividing by a number
            if other in [0, 0.0]:
                # if dividing by zero, raise an error
                raise ZeroDivisionError(f'{self} cannot be divided by zero.')

            if other in [1, 1.0]:
                # if dividing by 1, return self
                return self

            if self.case in [PCase.NEGNUM, PCase.NUM]:
                # if self is a number, just find the modulus
                # let P handle the rest
                p = P(*self.index, _=self._[-1] % other, **self.args)
                p.name = f'{self} % {other}'
                return p

            p = P(*self.index, _=[i % other for i in self._], **self.args)
            p.name = f'{self} % {other}'
            return p

        if isinstance(other, list):
            if isinstance(other[0], tuple):
                raise ValueError(
                    "Cannot divide by a list of tuples. Please provide a valid parameter, variable, or number."
                )

            if self.case in [PCase.NUM, PCase.NEGNUM]:
                # if self is a number, find the mod of self and each number in the list
                p = P(*self.index, _=[self._[-1] % i for i in other], **self.args)

            else:
                if len(self) != len(other):
                    warn(
                        f"Index mismatch {self} % {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                    )
                # if list and self is a set, just zip through
                p = P(
                    *self.index, _=[i % j for i, j in zip(self._, other)], **self.args
                )
                # change the name to add that something from a list has been added
            p.name = f'{self} % φ'
            return p

        if isinstance(other, tuple):
            # dividing by parametric variable
            raise ValueError(
                f"Cannot divide {self} by a tuple. Please provide a valid parameter, variable, or number."
            )

        if isinstance(other, P):

            if self.case == PCase.ZERO:
                # if self is zero, return zero
                return 0

            if other.case == PCase.ZERO:
                raise ZeroDivisionError(f'{self} cannot be divided by zero.')

            if self.case in [PCase.NEGNUM, PCase.NUM]:
                if other.case in [PCase.NUM, PCase.NEGNUM]:
                    # if both are numbers
                    # let P handle the case
                    return P(*self.index, _=self._[-1] % other._[-1], **self.args)

                p = P(*self.index, _=[self._[-1] % i for i in other._], **self.args)
                p.name = f'{self} % {other}'
                return p
            if other.case in [PCase.NUM, PCase.NEGNUM]:
                # if other is a number, find the modulus of every value in self with the number
                p = P(*self.index, _=[i % other._[-1] for i in self._], **self.args)
                p.name = f'{self} % {other}'
                return p
            if len(self) != len(other):
                raise ValueError(
                    f"Index mismatch {self} % {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                )
            # if both are just general parameters
            # zip through the values and find the modulus
            p = P(*self.index, _=[i % j for i, j in zip(self._, other._)], **self.args)
            p.name = f'{self} % {other}'
            return p

        # else let the other handle the modulus
        return self % other

    def __pow__(
        self,
        other: (
            V
            | Self
            | T
            | F
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> P:

        if other is None:
            # if raising to None, return self
            return self

        if self.case == PCase.ZERO:
            # if self is zero, return zero
            return 0

        if isinstance(other, (int, float)):
            # if raising to power of a number
            if other in [0, 0.0]:
                # if raising to zero, return 1
                return 1

            if other in [1, 1.0]:
                # if raising to one, return self
                return self
            if self.case in [PCase.NEGNUM, PCase.NUM]:
                # if self is a number, just find the power
                # let P handle the rest
                return P(*self.index, _=self._[-1] ** other, **self.args)

            # else find the power of each element in set raised to other
            p = P(*self.index, _=[i**other for i in self._], **self.args)
            p.name = f'{self}^({other})'
            return p

        if isinstance(other, list):
            if isinstance(other[0], tuple):
                raise ValueError(
                    "Cannot raise to a list of tuples. Please provide a valid parameter, variable, or number."
                )

            if self.case in [PCase.NUM, PCase.NEGNUM]:
                p = P(*self.index, _=[self._[-1] ** i for i in other], **self.args)
            else:
                if len(self) != len(other):
                    warn(
                        f"Index mismatch {self} ^ {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                    )
                # if list, just zip through the values and raise to power
                p = P(*self.index, _=[i**j for i, j in zip(self._, other)], **self.args)
            # change the name to add that something from a list has been added
            p.name = f'{self}^φ'
            return p

        if isinstance(other, tuple):
            # setting to the power of a parametric variable
            raise ValueError(
                f"Cannot raise {self} to a tuple. Please provide a valid parameter, variable, or number."
            )

        if isinstance(other, P):
            # other is a parameter set
            if other.case == PCase.ZERO:
                # if other is 0
                return 1

            if self.case in [PCase.NEGNUM, PCase.NUM]:
                # if self is a number, just find the power
                # let P handle the rest
                if other.case in [PCase.NUM, PCase.NEGNUM]:
                    return P(*self.index, _=self._[-1] ** other._[-1], **self.args)

                p = P(*self.index, _=[self._[-1] ** i for i in other._], **self.args)
                p.name = f'{self}^{other}'
                return p

            if other.case in [PCase.NUM, PCase.NEGNUM]:
                # if other is a number, raise every value in self to the power of the number
                p = P(*self.index, _=[i ** other._[-1] for i in self._], **self.args)
                p.name = f'{self}^{other}'
                return p

            if len(self) != len(other):
                raise ValueError(
                    f"Index mismatch {self} ^ {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                )
            # if both are just general parameters
            # zip through the values and raise to power
            p = P(*self.index, _=[i**j for i, j in zip(self._, other._)], **self.args)
            p.name = f'{self}^{other}'
            return p

        # else let the other handle the power
        # not sure if this will ever be called tbh
        return self**other

    # -----------------------------------------------------
    #                    Relational
    # -----------------------------------------------------

    def __eq__(
        self,
        other: (
            Self
            | P
            | T
            | F
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> bool:

        if isinstance(other, (int, float)):

            if other in [0, 0.0]:
                if self.case == PCase.ZERO:
                    # if self is zero, return True
                    return True

            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                # if self is a number, compare it with the last value
                return self._[-1] == other
            # if not numeric, False
            raise NotImplementedError(
                f'{self} == {other}: cannot compare a parameter set with a number'
            )

        if isinstance(other, list):
            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                raise NotImplementedError(
                    f'{self} == {other}: cannot compare a number with a list.'
                )
            # if self is a set, compare it with the list
            if len(self) != len(other):
                warn(
                    f"Index mismatch {self} == {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                )
            return all([i == j for i, j in zip(self._, other)])

        if isinstance(other, P):
            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:

                if other.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                    # if self is a number, compare it with the last value of other
                    return self._[-1] == other._[-1]

                raise NotImplementedError(
                    f'{self} == {other}: cannot compare a number with a parameter set.'
                )

            if len(self) != len(other):
                warn(
                    f"Index mismatch {self} == {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                )

            return all([i == j for i, j in zip(self._, other._)])
        # else let other handle this
        return self == other

    def __le__(
        self,
        other: (
            Self
            | P
            | T
            | F
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> bool:

        if isinstance(other, (int, float)):

            if other in [0, 0.0]:
                if self.case in [PCase.ZERO, PCase.NEGNUM, PCase.NEGSET]:
                    # if self is zero or negative number, return True
                    return True

                if self.case in [PCase.NUM, PCase.SET]:
                    # if self is a positive number or set, return False
                    return False

            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                # if self is a number, compare it with the last value
                return self._[-1] <= other
            # if not numeric, False
            raise NotImplementedError(
                f'{self} <= {other}: cannot compare a parameter set with a number'
            )

        if isinstance(other, list):
            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                raise NotImplementedError(
                    f'{self} <= {other}: cannot compare a number with a list.'
                )
            # if self is a set, compare it with the list
            if len(self) != len(other):
                warn(
                    f"Index mismatch {self} <= {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                )
            return all([i <= j for i, j in zip(self._, other)])

        if isinstance(other, P):
            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:

                if other.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                    # if self is a number, compare it with the last value of other
                    return self._[-1] <= other._[-1]

                raise NotImplementedError(
                    f'{self} <= {other}: cannot compare a number with a parameter set.'
                )

            if len(self) != len(other):
                warn(
                    f"Index mismatch {self} <= {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                )

            return all([i <= j for i, j in zip(self._, other._)])
        # else let other handle this
        return self <= other

    def __ge__(
        self,
        other: (
            Self
            | P
            | T
            | F
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> bool:
        if isinstance(other, (int, float)):

            if other in [0, 0.0]:
                if self.case in [PCase.NEGNUM, PCase.NEGSET]:
                    # if self negative number or negated set, return False
                    return False

                if self.case in [PCase.ZERO, PCase.NUM, PCase.SET]:
                    # if self is a positive number or set, return True
                    return True

            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                # if self is a number, compare it with the last value
                return self._[-1] >= other
            # if not numeric, False
            raise NotImplementedError(
                f'{self} >= {other}: cannot compare a parameter set with a number'
            )

        if isinstance(other, list):
            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                raise NotImplementedError(
                    f'{self} >= {other}: cannot compare a number with a list.'
                )
            # if self is a set, compare it with the list
            if len(self) != len(other):
                warn(
                    f"Index mismatch {self} >= {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                )
            return all([i >= j for i, j in zip(self._, other)])

        if isinstance(other, P):
            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:

                if other.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                    # if self is a number, compare it with the last value of other
                    return self._[-1] >= other._[-1]

                raise NotImplementedError(
                    f'{self} >= {other}: cannot compare a number with a parameter set.'
                )

            if len(self) != len(other):
                warn(
                    f"Index mismatch {self} >= {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                )

            return all([i >= j for i, j in zip(self._, other._)])
        # else let other handle this
        return self >= other

    def __lt__(
        self,
        other: (
            Self
            | P
            | T
            | F
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> bool:
        if isinstance(other, (int, float)):

            if other in [0, 0.0]:

                if self.case in [PCase.NEGNUM, PCase.NEGSET]:
                    # if self negative number or negated set, return True
                    return True

                if self.case in [PCase.ZERO, PCase.NUM, PCase.SET]:
                    # if self is a positive number or set, return True
                    return False

            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                # if self is a number, compare it with the last value
                return self._[-1] < other
            # if not numeric, False
            raise NotImplementedError(
                f'{self} < {other}: cannot compare a parameter set with a number'
            )

        if isinstance(other, list):
            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                raise NotImplementedError(
                    f'{self} < {other}: cannot compare a number with a list.'
                )
            # if self is a set, compare it with the list
            if len(self) != len(other):
                warn(
                    f"Index mismatch {self} < {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                )
            return all([i < j for i, j in zip(self._, other)])

        if isinstance(other, P):
            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:

                if other.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                    # if self is a number, compare it with the last value of other
                    return self._[-1] < other._[-1]

                raise NotImplementedError(
                    f'{self} < {other}: cannot compare a number with a parameter set.'
                )

            if len(self) != len(other):
                warn(
                    f"Index mismatch {self} < {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                )

            return all([i < j for i, j in zip(self._, other._)])
        # else let other handle this
        return self < other

    def __ne__(
        self,
        other: (
            Self
            | P
            | T
            | F
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> bool:
        if isinstance(other, (int, float)):

            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                # if self is a number, compare it with the last value
                return self._[-1] != other
            # if not numeric, False
            raise NotImplementedError(
                f'{self} != {other}: cannot compare a parameter set with a number'
            )

        if isinstance(other, list):
            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                raise NotImplementedError(
                    f'{self} != {other}: cannot compare a number with a list.'
                )
            # if self is a set, compare it with the list
            if len(self) != len(other):
                warn(
                    f"Index mismatch {self} != {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                )
            return all([i != j for i, j in zip(self._, other)])

        if isinstance(other, P):
            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:

                if other.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                    # if self is a number, compare it with the last value of other
                    return self._[-1] != other._[-1]

                raise NotImplementedError(
                    f'{self} != {other}: cannot compare a number with a parameter set.'
                )

            if len(self) != len(other):
                warn(
                    f"Index mismatch {self} != {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                )

            return all([i != j for i, j in zip(self._, other._)])
        # else let other handle this
        return self != other

    def __gt__(
        self,
        other: (
            Self
            | P
            | T
            | F
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> bool:
        if isinstance(other, (int, float)):

            if other in [0, 0.0]:

                if self.case in [PCase.ZERO, PCase.NEGNUM, PCase.NEGSET]:
                    # if self negative number or negated set, return True
                    return False

                if self.case in [PCase.NUM, PCase.SET]:
                    # if self is a positive number or set, return True
                    return True

            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                # if self is a number, compare it with the last value
                return self._[-1] > other
            # if not numeric, False
            raise NotImplementedError(
                f'{self} > {other}: cannot compare a parameter set with a number'
            )

        if isinstance(other, list):
            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                raise NotImplementedError(
                    f'{self} > {other}: cannot compare a number with a list.'
                )
            # if self is a set, compare it with the list
            if len(self) != len(other):
                warn(
                    f"Index mismatch {self} > {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                )
            return all([i > j for i, j in zip(self._, other)])

        if isinstance(other, P):
            if self.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:

                if other.case in [PCase.NUM, PCase.NEGNUM, PCase.ZERO]:
                    # if self is a number, compare it with the last value of other
                    return self._[-1] > other._[-1]

                raise NotImplementedError(
                    f'{self} > {other}: cannot compare a number with a parameter set.'
                )

            if len(self) != len(other):
                warn(
                    f"Index mismatch {self} > {other}: len(self) ({len(self)}) != len(other) ({len(other)})"
                )

            return all([i > j for i, j in zip(self._, other._)])
        # else let other handle this
        return self > other

    # -----------------------------------------------------
    #                    Vector
    # -----------------------------------------------------

    def __iter__(self) -> Self:
        return iter(self._)

    def __len__(self):
        return len(self.map)

    def __call__(self, *key: I) -> Self:

        def lister(inp: tuple[I]) -> tuple[I | list[V]]:
            return tuple([i] if isinstance(i, V) else i for i in inp)

        # if a dependent variable is being passed in the key
        # extract variable from the index (it will be in a list)
        def delister(inp: tuple[I | list[V]]):
            return tuple(i[0] if isinstance(i, list) else i for i in inp)

        if not key or delister(key) == delister(self.index):
            # if the index is an exact match
            # or no key is passed
            return self

        # the check helps to handle if a variable itself is an index
        # we do not want to iterate over the entire variable set
        # but treat the variable as a single index element
        key: tuple[I] | set[tuple[I]] = lister(key)

        # if a subset is passed,
        # first create a product to match
        # the indices

        # create a new variable set to return
        p = P(**self.args)
        p.name, p.n = self.name, self.n
        p.index = key

        # should be able to map these
        for index in product(*key):
            # this helps weed out any None indices
            # i.e. skips
            if any(i is None for i in index):
                index = None

            if index is None:
                parameter = None
            else:
                parameter = self.map[index]

            p.map[index] = parameter
            p._.append(parameter)

        return p

    def __getitem__(self, pos: int) -> float | int:
        return self._[pos]

    # -----------------------------------------------------
    #                    Hashing
    # -----------------------------------------------------

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self.name)

    def __hash__(self):
        return hash(str(self.name))

    # -----------------------------------------------------
    #                    Export
    # -----------------------------------------------------

    def sympy(self):
        """symbolic representation"""
        if has_sympy:
            return IndexedBase(str(self))[
                symbols(",".join([f'{d}' for d in self.index]), cls=Idx)
            ]
        print(
            "sympy is an optional dependency, pip install gana[all] to get optional dependencies"
        )

    def pyomo(self):
        """Pyomo representation"""
        # idx = [i.pyomo() for i in self.index]
        # return PyoParam(*idx, initialize=self._, doc=str(self))
        if has_pyomo:
            return PyoParam(
                initialize=self._,
                doc=str(self),
            )
        print(
            "pyomo is an optional dependency, pip install gana[all] to get optional dependencies"
        )
