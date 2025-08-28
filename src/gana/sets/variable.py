"""Continuous Variable"""

from __future__ import annotations

from itertools import product
from math import prod
from typing import TYPE_CHECKING, Self


from .birth import make_P, make_T

from IPython.display import Math, display
from copy import deepcopy

from .cases import Elem, FCase
from .constraint import C
from .function import F
from .index import I

if TYPE_CHECKING:
    from .objective import O
    from .parameter import P
    from .theta import T

try:
    from pyomo.environ import (
        Binary,
        Integers,
        NonNegativeIntegers,
        NonNegativeReals,
        Reals,
    )
    from pyomo.environ import Var as PyoVar

    has_pyomo = True
except ImportError:
    has_pyomo = False

try:
    from sympy import Idx, IndexedBase, Symbol, symbols

    has_sympy = True
except ImportError:
    has_sympy = False

try:
    from matplotlib import pyplot as plt
    from matplotlib import rc

    has_matplotlib = True

except ImportError:
    has_matplotlib = False


class V:
    """Ordered set of variables (Var)

    Args:
        *index (I, optional): Indices. Defaults to None.
        itg (bool, optional): If the variable set is integer. Defaults to False.
        nn (bool, optional): If the variable set is non-negative. Defaults to True.
        bnr (bool, optional): If the variable set is binary. Defaults to False.
        mutable (bool, optional): If the variable set is mutable. Defaults to False.
        tag (str): Tag/details
        ltx (str): LaTe representation of the variable set.

    Attributes:
        index (I): Index of the variable set. Product of all indices.
        map (dict[I , V]): Index to variable mapping.
        _ (list[V]): List of variables in the set.
        itg (bool): Integer variable set.
        nn (bool): Non-negative variable set.
        bnr (bool): Binary variable set.
        mutable (bool): Mutable variable set.
        tag (str): Tag/details.
        name (str): Name, set by the program.
        n (int): Number id, set by the program.
        args (dict[str, bool]): Arguments to pass when making similar variable sets. itg, nn, bnr.
        ltx (str): LaTeX representation of the variable set.

    Raises:
        ValueError: If variable is binary and not non-negative
        ValueError: multiplication by tuple
        ValueError: multiplication by list of tuples tuple
        ValueError: Division by None
        ZeroDivisionError: Division by zero
        ValueError: Division by tuple
        ValueError: Division by list of tuples tuple
        ValueError: Division of something by a variable
        ValueError: Raising variable to a power, except 0 or 1

    """

    def __init__(
        self,
        *index: I,
        itg: bool = False,
        nn: bool = True,
        bnr: bool = False,
        mutable: bool = False,
        tag: str = None,
        ltx: str = None,
    ):
        # these are always given during declaration
        self.tag = tag
        # integer variable set
        self.itg = itg
        # non-negative variable set
        self.bnr = bnr
        # latex representation
        self._ltx = ltx

        if self.bnr:
            self.itg = bnr
            if not nn:
                raise ValueError('Binary variables must be non-negative')

        self.nn = nn
        self.mutable = mutable

        # a variable set of size 1 is a scalar variable
        # these are created at each index in the set
        # their position in the parent set is recorded
        # Example: if v = V(I('i', 'j')) then v._ = [V(I('i)), V(I('j'))]
        self.parent: Self = None
        self.pos: int = None
        self._: list[Self] = []

        # set by program
        self.name: str = ''

        # the check helps to handle if a variable itself is an index
        # we do not want to iterate over the entire variable set
        # but treat the variable as a single index element
        self.index: tuple[I] | set[tuple[I]] = tuple(
            [i if not isinstance(i, V) else [i] for i in index]
        )

        if self.index:
            self.map: dict[I, V] = {
                prod([ii for ii in i if ii is not None]): None
                for i in list(product(*self.index))
            }
            # self.map: dict[I, V] = {prod(i): None for i in list(product(*self.index))}
        else:
            self.map: dict[I, V] = {}

        # this is the nth parameter declared in the
        self.n: int = None

        # updated by the constraint
        # what constraints constrain this variable
        self.cons_by: list[C] = []

        # which objectives minimize it (gana is always min)
        self.min_by: list[O] = []

        # value after optimization
        self.value = None

        # these keep variables consistent with functions for some operations
        # Take the example of a variable set - parameter set
        # [v0 - 2, v1 - 0, v2 + 4]
        # at positions 0 and 2, we have functions
        # at position 1, v1 - 0 = v1, which is a variable
        # these attribute evades the need for an instance check
        self.variables = [self]
        self.elements = [self]
        self.struct = (Elem.V, None)
        self.case = FCase.VAR
        # TODO: check
        self.X = [self.n]

        self.copyof: Self = None

        # this flag tells the function
        # that self in its entirety is being returned on call
        # thus a copy needs to be made in the function
        # this prevents the entirety of self being an element of a function
        # as variables can mutate in gana
        self.make_copy: bool = False

    @property
    def matrix(self) -> dict:
        """Matrix Representation"""
        if self.parent:
            return {self.n: 1}

        return {v: self.matrix for v in self._}

    @property
    def args(self) -> dict[str, str | bool]:
        """Return the arguments of the variable set"""
        return {
            'itg': self.itg,
            'nn': self.nn,
            'bnr': self.bnr,
            'mutable': self.mutable,
            'tag': self.tag,
            'ltx': self.ltx,
        }

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
        return [[1] if self._[i] is not None else [] for i in range(len(self))]
        # return [
        #     [
        #         1 if i == j and list(self.map)[i] iif self._[i] is not Nones not None else 0
        #         for j in range(len(self))
        #     ]
        #     for i in range(len(self))
        # ]

    @property
    def features_in(self) -> list[C | O]:
        """Constraints and objectives that this variable set is part of"""
        return self.cons_by + self.min_by

    # -----------------------------------------------------
    #                   Birthing
    # -----------------------------------------------------

    def make_function(self) -> F:
        """Make a function"""
        return F(
            one=make_P(1, self.index),
            mul=True,
            two=self,
            one_type=Elem.P,
            two_type=Elem.V,
            case=FCase.FVAR,
        )

    def copy(self) -> V:
        """Returns a copy of the variable set"""
        v = V(**self.args)
        v.name, v.n = self.name, self.n
        v.index = tuple(self.index)
        v.map = self.map.copy()
        v._ = list(self._)
        v.copyof = self
        return v

    def birth_variables(self, mutating: bool = False, n_start: int = 0):
        """Births a variable at every index in the index set

        Args:
            mutating (bool, optional): If the variable set is being mutated. Defaults to False.
            n_start (int, optional): The starting number for positioning the variables. Defaults to 0.
        """
        for pos, idx in enumerate(self.map):
            # create a variable at each index
            variable = V(**self.args)

            # set the parent to self
            variable.parent = self
            # for mutations variable names
            # and positions will be set based on
            # the existing variable.

            # this is the nth variable declared
            variable.n = n_start + pos

            if not mutating:
                # give the same name as self
                variable.name = rf'{self}[{pos}]'

                # this is the position in the parent set
                variable.pos = pos

            # set the new variable's index
            variable.index = idx

            # the new variable set has only
            # one variable itself
            # I get that this is like a recursive definition
            variable._ = [variable]

            # append to the set of variables of self
            self._.append(variable)

            # update the index mapping
            self.map[idx] = variable
            variable.map[idx] = variable

    # -----------------------------------------------------
    #                    Solution
    # -----------------------------------------------------

    def sol(self, aslist: bool = False) -> list[float] | None:
        """Solution
        Args:
            aslist (bool, optional): Returns values taken as list. Defaults to False.
        """
        if aslist:
            return [v.value for v in self._]
        for v in self._:
            display(Math(v.latex() + r'=' + rf'{v.value}'))

    # -----------------------------------------------------
    #                    Printing
    # -----------------------------------------------------

    def latex(self, index_only: bool = False) -> str:
        """LaTeX representation"""
        index = (
            r'_{'
            + rf'{self.index}'.replace('), (', '|').replace('(', '')
            .replace(')', '')
            .replace('[', '{')
            .replace(']', '}')
            + r'}'
        )

        if index_only:
            # if only index is requested
            # return the index in latex format
            return index

        if len(self.index) == 1:
            # if there is a single index element
            # then a comma will show up in the end, replace that
            return self.ltx + index.replace(',', '')  # type: ignore

        return self.ltx + index

    def show(self, descriptive: bool = False):
        """Display the variables
        Args:
            descriptive (bool, optional): Displays all variables in the ordered set. Defaults to False.
        """
        if descriptive:
            for v in self._:
                if v:
                    display(Math(v.latex()))
        else:
            display(Math(self.latex()))

    def mps(self):
        """Name in MPS file"""
        if self.bnr:
            return f'X{self.n}'
        return f'V{self.n}'

    def lp(self) -> str:
        """LP representation"""
        return str(self)

    @property
    def longname(self) -> str:
        """Long name"""
        if self.parent:
            return f'{self.parent.name}(' + ",".join([i.name for i in self.index]) + ')'
        return f'{self.name}(' + ",".join([i.name for i in self.index]) + ')'

    # -----------------------------------------------------
    #                    Birthers
    # -----------------------------------------------------

    def report(self) -> V:
        """Return a reporting binary variable"""
        return V(
            *self.index,
            bnr=True,
            tag=f'Reporting binary for {self.tag}',
            ltx=rf'x_{self.ltx}',
        )

    # -----------------------------------------------------
    #                    Operators
    # -----------------------------------------------------

    def __neg__(self) -> F:
        # doing this here saves some time
        # let the function know that you are passing something consistent already
        # saves time

        f = F(
            one=make_P(-1, self.index),
            mul=True,
            two=self,
            one_type=Elem.P,
            two_type=Elem.V,
            case=FCase.NEGVAR,
            consistent=True,
        )
        return f

    def __add__(
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
    ) -> Self | F:

        if other is None:
            # if adding to nothing, return self
            # Duh
            return self

        if isinstance(other, (int, float)):
            # if adding to number, convert to P
            if other in [0, 0.0]:
                # if adding to zero, return self
                return self
            return F(
                one=self,
                add=True,
                two=make_P(other, self.index),
                one_type=Elem.V,
                two_type=Elem.P,
                consistent=True,
            )

        if isinstance(other, tuple):
            # if adding to a tuple, convert to T
            return F(
                one=self,
                add=True,
                two=make_T(other, index=self.index),
                one_type=Elem.V,
                two_type=Elem.T,
                consistent=True,
            )

        if isinstance(other, list):
            if isinstance(other[0], tuple):
                # if list of tuples
                # This does not allow for parametric variables and parameters
                # to be set sporadically across the index
                # that would take all instances in a list of be checked
                # which would be time consuming
                # Could make it an optional feature in the future
                return F(
                    one=self,
                    add=True,
                    two=make_T(other),
                    one_type=Elem.V,
                    two_type=Elem.T,
                    consistent=True,
                )
            else:
                return F(
                    one=self,
                    add=True,
                    two=make_P(other),
                    one_type=Elem.V,
                    two_type=Elem.P,
                    consistent=True,
                )

        return F(one=self, add=True, two=other, one_type=Elem.V)

    def __radd__(
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
    ) -> Self | F:
        # radd will only be called by non gana elements
        # default to add
        return self + other

    def __sub__(
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
    ) -> Self | F:
        if other is None:
            # if subtracting nothing from variable
            # return self
            return self

        if isinstance(other, (int, float)):
            # if subtracting a number, convert to P
            if other in [0, 0.0]:
                # if subtracting zero, return self
                return self

            return F(
                one=self,
                sub=True,
                two=make_P(other, self.index),
                one_type=Elem.V,
                two_type=Elem.P,
                consistent=True,
            )

        if isinstance(other, tuple):
            # if subtracting a tuple, convert to T
            return F(
                one=self,
                sub=True,
                two=make_T(other, index=self.index),
                one_type=Elem.V,
                two_type=Elem.T,
                consistent=True,
            )

        if isinstance(other, list):
            if isinstance(other[0], tuple):
                # This does not allow for parametric variables and parameters
                # to be set sporadically across the index
                # that would take all instances in a list of be checked
                # which would be time consuming
                # Could make it an optional feature in the future
                return F(
                    one=self,
                    sub=True,
                    two=make_T(other),
                    one_type=Elem.V,
                    two_type=Elem.T,
                    consistent=True,
                )
            else:
                return F(
                    one=self,
                    sub=True,
                    two=make_P(other),
                    one_type=Elem.V,
                    two_type=Elem.P,
                    consistent=True,
                )

        return F(one=self, sub=True, two=other, one_type=Elem.V)

    def __rsub__(
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
    ) -> Self | F:
        if other in [0, 0.0, None]:
            return -self
        else:
            # this is only called for non gana elements (lists, ints, floats, tuples)
            # as other - variable
            if isinstance(other, (int, float)) and other < 0:
                # if other is (int, float) and is negative
                # then -other - V should be -V - other
                return -self - (-other)
            # otherwise, it is  -V + other
            return -self + other

    def __mul__(
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
    ) -> Self | F | float:
        if other is None:
            # multiplying by nothing
            # gives nothing
            return

        if isinstance(other, (int, float)):
            # multiplying by zero, gives 0
            if other in [0, 0.0]:
                return 0.0
            # multiplying by unity, gives itself
            if other in [1, 1.0]:
                return self

            # multiplying by negative unity, gives -negation
            if other in [1, -1.0]:
                return -self
            # let multiplication always be P*V
            return F(
                one=make_P(other, self.index),
                mul=True,
                two=self,
                one_type=Elem.P,
                two_type=Elem.V,
                consistent=True,
            )
        if isinstance(other, tuple):
            # TODO multiplying by a tuple
            raise ValueError(
                f'{self}*{other}: Multiplication with multiparameteric variable is not supported yet'
            )

        if isinstance(other, list):
            if isinstance(other[0], tuple):
                # TODO multiplying by a list of tuples
                raise ValueError(
                    f'{self}*{other}: Multiplication with multiparameteric variable is not supported yet'
                )
            else:
                return F(
                    one=make_P(other),
                    mul=True,
                    two=self,
                    one_type=Elem.P,
                    two_type=Elem.V,
                    consistent=True,
                )

        from .parameter import P

        if isinstance(other, P):
            # multiplying by a parameter, make it a function
            # always keep the parameter upfront for multiplication
            return F(one=other, mul=True, two=self, one_type=Elem.P, two_type=Elem.V)
        return F(one=self, mul=True, two=other, one_type=Elem.V)

    def __rmul__(
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
    ) -> Self | F | float:
        # only called for non gana elements (tuple, list, int, float)
        # multiplication is commutative
        return self * other

    def __truediv__(
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
    ) -> Self | F:
        if other is None:
            raise ValueError("Cannot divide by None")

        if isinstance(other, (int, float)):
            # dividing by zero, raises error
            if other in [0, 0.0]:
                raise ZeroDivisionError("Cannot divide by zero")
            # dividing by unity, gives itself
            if other in [1, 1.0]:
                return self
            # dividing by negative unity, gives -negation
            if other in [-1, -1.0]:
                return -self
            # else make this a multiplication by reciprocal
            return F(
                one=make_P(1 / other, self.index),
                mul=True,
                two=self,
                one_type=Elem.P,
                two_type=Elem.V,
                consistent=True,
            )

        if isinstance(other, tuple):
            # TODO division by tuple
            raise ValueError('Division by tuple is not supported yet, use T instead')

        if isinstance(other, list):
            # TODO division by list of tuples
            if isinstance(other[0], tuple):
                raise ValueError(
                    'Division by tuple is not supported yet, use T instead'
                )
            return F(
                one=make_P([1 / o for o in other]),
                mul=True,
                two=self,
                one_type=Elem.P,
                two_type=Elem.V,
                consistent=True,
            )

        return F(one=self, div=True, two=other, one_type=Elem.V)

    def __rtruediv__(
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
    ):
        # TODO nonlinear stuff
        raise ValueError(
            "Division of something by a variable, non-linear operations are not supported yet"
        )

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
            | I
        ),
    ) -> C:

        if isinstance(other, I):
            # variables can be passed as indices
            return self.name == other.name

        # if something of the type v = p*v is given
        # classify it as a calculation
        if isinstance(other, V):
            other = other.make_function()

        if (
            isinstance(other, F)
            and other.one_type == Elem.P
            and other.two_type == Elem.V
            and other.mul
        ):
            other.case = FCase.CALC
            other.calculation = self.copy()
            other.index = self.index
            return other

        return C(self - other)

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
    ) -> C:
        return C(self - other, leq=True)

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
    ):
        return C(other - self, leq=True)

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
    ) -> C:
        return self <= other

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
    ) -> C:
        return self >= other

    def __pow__(
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
    ) -> C:
        if other is None:
            # raising to nothing, return self
            return self
        if isinstance(other, (int, float)):
            if other in [0, 0.0]:
                # variable raised to 0 is 1
                return 1.0
            if other in [1, 1.0]:
                # variable raised to 1 is itself
                return self

        # f = self
        # for _ in range(other - 1):
        #     f *= self
        # return f
        # TODO nonlinear stuff
        raise ValueError(
            "Raising variable to a power, non-linear operations are not supported yet"
        )

    # -----------------------------------------------------
    #                    Vector
    # -----------------------------------------------------

    def __iter__(self) -> Self:
        """Iterate over the variables in the set"""
        return iter(self._)

    def __len__(self) -> int:
        return len(self._)

    def __call__(self, *key: I) -> Self:

        # if a dependent variable is being passed in the key
        # extract variable from the index (it will be in a list)
        def delister(inp: tuple[I | list[V]]):
            return tuple(i[0] if isinstance(i, list) else i for i in inp)

        if not key or delister(key) == delister(self.index):
            # if the index is an exact match
            # or no key is passed
            self.make_copy = True
            return self

        # the check helps to handle if a variable itself is an index
        # we do not want to iterate over the entire variable set
        # but treat the variable as a single index element
        key: tuple[I] | set[tuple[I]] = [
            i if not isinstance(i, V) else [i] for i in key
        ]

        # if a subset is passed,
        # first create a product to match
        # the indices

        indices = list(product(*key))
        # create a new variable set to return
        v = V(**self.args)
        v.name, v.n = self.name, self.n
        v.index = tuple(key)

        # should be able to map these
        for index in indices:
            # this helps weed out any None indices
            # i.e. skips
            if any(i is None for i in index):
                index = None

            if index is None:
                variable = None
            else:
                variable = self.map[index]
            v.map[index] = variable
            v._.append(variable)

        return v

    def __getitem__(self, pos: int) -> V:
        return self._[pos]

    # -----------------------------------------------------
    #                    Hashing
    # -----------------------------------------------------

    def __str__(self):
        return rf'{self.name}'

    def __repr__(self):
        return str(self.name)

    def __hash__(self):
        return hash(self.name)

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
        if has_pyomo:
            idx = [i.pyomo() for i in self.index]
            if self.bnr:
                return PyoVar(*idx, domain=Binary, doc=str(self))

            elif self.itg:
                if self.nn:
                    return PyoVar(*idx, domain=NonNegativeIntegers, doc=str(self))
                else:
                    return PyoVar(*idx, domain=Integers, doc=str(self))

            else:
                if self.nn:
                    return PyoVar(*idx, domain=NonNegativeReals, doc=str(self))
                else:
                    return PyoVar(*idx, domain=Reals, doc=str(self))
        print(
            "pyomo is an optional dependency, pip install gana[all] to get optional dependencies"
        )

    def draw(
        self,
        kind: str = 'line',
        font_size: float = 16,
        fig_size: tuple[float, float] = (12, 6),
        linewidth: float = 0.7,
        color: str = 'blue',
        grid_alpha: float = 0.3,
        usetex: bool = True,
    ):
        """Plot the variable set

        Args:
            kind (str, optional): Type of plot ['line', 'bar']. Defaults to 'line'.
            font_size (float, optional): Font size for the plot. Defaults to 16.
            fig_size (tuple[float, float], optional): Size of the figure. Defaults to (12, 6).
            linewidth (float, optional): Width of the line in the plot. Defaults to 0.7.
            color (str, optional): Color of the line in the plot. Defaults to 'blue'.
            grid_alpha (float, optional): Transparency of the grid lines. Defaults to 0.3.
            usetex (bool, optional): Use LaTeX for text rendering. Defaults to True.


        """

        if not has_matplotlib:
            print(
                "matplotlib is an optional dependency, pip install gana[all] to get optional dependencies"
            )
            return

        ax = plt.subplots(figsize=fig_size)[1]

        # the indices are the x-axis
        x = [str(idx) for idx in self.map]
        # the values are the y-axis
        y = self.sol(True)

        if usetex:
            rc(
                'font',
                **{'family': 'serif', 'serif': ['Computer Modern'], 'size': font_size},
            )
            rc('text', usetex=usetex)
        else:
            rc('font', **{'size': font_size})

        if kind == 'line':
            ax.plot(x, y, linewidth=linewidth, color=color)

        elif kind == 'bar':
            ax.bar(x, y, linewidth=linewidth, color=color)

        ax.set_title(rf'${self.latex()}$')
        ax.set_ylabel(r'Values')
        ax.set_xlabel(r'Indices')
        ax.grid(alpha=grid_alpha)
        ax.set_xticks(x)
        ax.set_xticklabels(
            [
                rf'${tuple([idx.latex() for idx in index])}$'.replace("'", "").replace(
                    '\\', ''
                )
                for index in self.map
            ]
        )

        plt.rcdefaults()

    def draw_line(self, **kwargs):
        """Alias for plot with kind='line'"""
        self.draw(kind='line', **kwargs)

    def draw_bar(self, **kwargs):
        """Alias for plot with kind='bar'"""
        self.draw(kind='bar', **kwargs)
