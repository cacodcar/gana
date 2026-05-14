# """Parametric variable"""

from __future__ import annotations

from itertools import product
# from functools import reduce
from math import prod
from typing import TYPE_CHECKING, Self
from warnings import warn

from IPython.display import Math, display

from ._element import _E
from .birth import make_P
from .cases import Elem
from .function import F
from .index import I
from .variable import V

if TYPE_CHECKING:
    from .parameter import P


class T(_E):
    """
    Ordered set of parametric variables (theta).

    :param index: Index for the theta set.
    :type index: I
    :param _: Values for the theta set.
    :type _: list[tuple[float]] | tuple[float]
    :param mutable: If True, the theta set can be modified. Defaults to False.
    :type mutable: bool, optional
    :param tag: Tag for the theta set. Defaults to None.
    :type tag: str, optional

    :ivar index: Index of the parametric variable set
    :vartype index: I
    :ivar _: List of parametric variables
    :vartype _: list[int | float]
    :ivar mutable: If the parametric variable set is mutable
    :vartype mutable: bool
    :ivar tag: Tag/details
    :vartype tag: str
    :ivar name: Name, set by the program
    :vartype name: str
    :ivar n: Number id, set by the program
    :vartype n: int
    :ivar map: Index to parameter mapping
    :vartype map: dict[X | Idx, Var]
    """

    def __init__(
        self,
        *index: I,
        _: list[tuple[float]] | tuple[float] = None,
        tag: str = None,
        mutable: bool = False,
        ltx: str = None,
        name: str = "",
    ):

        _E.__init__(self, *index, tag=tag, ltx=ltx, mutable=mutable, name=name)

        # name will be set by the program later
        # if dummy index, the name is set to 'φ' (phi)
        self.name = self.name or "θ"

        # containt the set of parameteric variables
        self._: list[Self] = _  # always a list of parameteric variables

        self.lb: float | int = None
        self.ub: float | int = None

        # flag to check if the set has been birthed
        self.birthed = False

    # -----------------------------------------------------
    #                    Helpers
    # -----------------------------------------------------

    @property
    def args(self) -> dict[str, str | bool]:
        """Return the arguments of the parametric variable set

        :returns: Dictionary of arguments
        :rtype: dict
        """
        return {"tag": self.tag, "ltx": self.ltx, "mutable": self.mutable}

    def create_map(self):
        """Create a map of indices to parameters"""
        self.map: dict[tuple[I], Self] = {
            prod(i): self._[n] for n, i in enumerate(list(product(*self.index)))
        }

    # -----------------------------------------------------
    #                    Birthing
    # -----------------------------------------------------

    def birth_thetas(self, mutating: bool = False, n_start=0):
        """Births a parametric variable (Theta) at every index in the index set

        :param mutating: If the variable set is being mutated. Defaults to False.
        :type mutating: bool, optional
        :param n_start: The starting number for positioning the variables. Defaults to 0.
        :type n_start: int, optional
        """
        for pos, idx in enumerate(self.map):
            # create a theta at every index

            theta = T(**self.args)

            # set parent to self
            theta.parent = self

            # this is the nth parametric variable set declared
            theta.n = n_start + pos

            if not mutating:
                # give self + pos as name
                theta.name = f"{self.name}[{pos}]"
                # give position
                theta.pos = pos

            # give the index
            theta.index = idx

            # kind of recursive, but for elemental sets
            # the element set only contains a tuple
            theta.lb = self._[pos][0]
            theta.ub = self._[pos][1]
            theta._ = [theta]

            # theta._ = self._[pos]

            # append the new parametric variable to the set
            self._[pos] = theta

            # update the maps for both self and theta
            self.map[idx] = theta
            theta.map[idx] = theta

        # set the birthing flag
        self.birthed = True

    # -----------------------------------------------------
    #                   Matrix
    # -----------------------------------------------------

    @property
    def CrA(self):
        """A matric of critical region"""
        CrA_UB = [[0] * len(self) for _ in range(len(self))]
        CrA_LB = [[0] * len(self) for _ in range(len(self))]

        for n in range(len(self)):
            CrA_UB[n][n] = 1.0
            CrA_LB[n][n] = -1.0

        CrA_ = []

        for n in range(len(self)):
            CrA_.append(CrA_UB[n])
            CrA_.append(CrA_LB[n])

        return CrA_

    @property
    def CrB(self):
        """B matrix of critical region"""
        CrB_ = []
        for t in self._:
            CrB_.append(t._[1])
            CrB_.append(-t._[0])

        return CrB_

    # -----------------------------------------------------
    #                    Printing
    # -----------------------------------------------------

    @property
    def ltx(self) -> str:
        """LaTeX representation of the parametric variable set"""
        if self._ltx:
            return r"{" + self._ltx + r"}"
        # if user has not set the LaTeX representation
        # the name becomes the latex representation
        if self.name:
            return r"{" + self.name.replace("_", r"\_") + r"}"
        return self._ltx

    @property
    def longname(self) -> str:
        """Long name representation"""
        if self.parent:
            return f"{self.parent.name}(" + ",".join([i.name for i in self.index]) + ")"
        return f"{self.name}(" + ",".join([i.name for i in self.index]) + ")"

    def latex(self) -> str:
        """LaTeX representation"""

        index = (
            r"_{"
            + rf"{self.index}".replace("(", "")
            .replace(")", "")
            .replace("[", "{")
            .replace("]", "}")
            + r"}"
        )

        if len(self.index) == 1:
            # if there is a single index element
            # then a comma will show up in the end, replace that
            return self.ltx + index.replace(",", "")  # type: ignore

        return self.ltx + index

    def show(self, descriptive: bool = False):
        """Display the variables

        :param descriptive: Print members of the index set
        :type descriptive: bool, optional
        """
        if descriptive:
            for pv in self._:
                if pv:
                    display(Math(pv.latex()))
        else:
            display(Math(self.latex()))

    # -----------------------------------------------------
    #                    Operations
    # -----------------------------------------------------

    def __neg__(self):
        return self * -1

    def __add__(self, other: Self | P | V):

        # type of instance of other
        two_type = None

        if isinstance(other, (int, float)):
            # if adding with numeric
            if other in [0, 0.0]:
                # return self is zero
                return self
            # else make parameter
            other = make_P(other, index=self.index)
            two_type = Elem.P

        if isinstance(other, tuple):
            # if tuple, make T
            other = T(*self.index, _=other, **self.args)
            two_type = Elem.T

        if isinstance(other, list):
            # if list..
            # check first element type
            if isinstance(other[0], tuple):
                # if tuple
                # make T
                other = T(_=other, **self.args)
                two_type = Elem.T
            else:
                # assume it is a list of numbers
                other = make_P(other)
                two_type = Elem.P

        # irrespective just make a function,
        # if type not passed function.types will figure out
        return F(one=self, add=True, two=other, one_type=Elem.T, two_type=two_type)

    def __sub__(self, other: Self | P | V):
        # type of instance of other
        two_type = None

        if isinstance(other, (int, float)):
            # if adding with numeric
            if other in [0, 0.0]:
                # return self is zero
                return self
            # else make parameter
            other = make_P(other, index=self.index)
            two_type = Elem.P

        if isinstance(other, tuple):
            # if tuple, make T
            other = T(*self.index, _=other, **self.args)
            two_type = Elem.T

        if isinstance(other, list):
            # if list..
            # check first element type
            if isinstance(other[0], tuple):
                # if tuple
                # make T
                other = T(_=other, **self.args)
                two_type = Elem.T
            else:
                # assume it is a list of numbers
                other = make_P(other)
                two_type = Elem.P

        # irrespective just make a function,
        # if type not passed function.types will figure out
        return F(one=self, sub=True, two=other, one_type=Elem.T, two_type=two_type)

    def __radd__(self, other: Self | P | V | F):
        return other + self

    def __rsub__(self, other: Self | P | V | F):
        return -self + other

    def __mul__(self, other: Self | F):

        if isinstance(other, (int, float)):
            if other in [1, 1.0]:
                # if one return self
                return self

            # else scale the bounds

            t = T(
                *self.index,
                _=[tuple([other * j for j in i]) for i in self._],
                **self.args,
            )
            t.name = f"{other}*{self}"
            return t

        if isinstance(other, tuple):
            # if tuple scale the bounds again
            t = T(
                *self.index,
                _=[(other[0] * i[0], other[1] * i[1]) for i in self._],
                **self.args,
            )
            t.name = f"{self}*θ"

        if isinstance(other, list):
            # if list..
            # scale and return
            # check length match
            if len(self) != len(other):
                warn(
                    f"Index mismatch for {self} * {other}: ({len(self)} != {len(other)})"
                )
            # check first element type
            if isinstance(other[0], tuple):
                # if tuple
                # make T
                t = T(
                    *self.index,
                    _=[(i[0] * j[0], i[1] * j[1]) for i, j in zip(self, other)],
                    **self.args,
                )
                t.name = f"{self}*θ"
                return t
            # otherwise assume numeric

            t = T(
                *self.index,
                _=[(i[0] * j, i[1] * j) for i, j in zip(self, other)],
                **self.args,
            )

        # else let other handle the operation

        return other * self

    def __rmul__(self, other: Self | F | int):
        return self * other

    def __truediv__(self, other: Self | F | int):

        if isinstance(other, (int, float)):
            if other in [1, 1.0]:
                # if one return self
                return self

            # else scale the bounds
            t = T(
                *self.index,
                _=[tuple([i / other for i in j]) for j in self._],
                **self.args,
            )
            t.name = f"{self}/{other}"
            return t

        if isinstance(other, tuple):
            # theta\theta not allowed
            raise NotImplementedError(
                "Division by tuple is not implemented for theta sets."
            )

        if isinstance(other, list):
            # if list..
            # scale and return
            # check length match
            if len(self) != len(other):
                warn(
                    f"Index mismatch for {self} / {other}: ({len(self)} != {len(other)})"
                )
            # check first element type
            if isinstance(other[0], tuple):
                # if tuple
                raise NotImplementedError(
                    "Division by list of tuples is not implemented for theta sets."
                )

            # otherwise assume numeric
            t = T(
                *self.index,
                _=[(i[0] / j, i[1] / j) for i, j in zip(self, other)],
                **self.args,
            )

        raise NotImplementedError(
            "Division by anything other than numeric is not implemented for theta sets."
        )

    # -----------------------------------------------------
    #                    Vector
    # -----------------------------------------------------

    def __call__(self, *key: I) -> Self:

        if not key or (key == self.index):
            # if the index is an exact match
            # or no key is passed
            return self

        # if a subset is passed,
        # first create a product to match
        # the indices
        indices = list(product(*key))

        # create a new variable set to return
        t = T(**self.args)
        t.name, t.n = self.name, self.n
        t.index = key

        # should be able to map these
        for index in indices:
            # this helps weed out any None indices
            # i.e. skips
            index = prod(index)
            if index is None:
                theta = None
            else:
                theta = self.map[index]
                t.map[index] = theta

            t._.append(theta)

        return t

    def __getitem__(self, pos: int) -> float | int:
        return self._[pos]

    def __iter__(self) -> Self:
        return iter(self._)

    def __len__(self):
        return len(self.map)

    # -----------------------------------------------------
    #                    Hashing
    # -----------------------------------------------------

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __hash__(self):
        try:
            return hash(self.name)
        except AttributeError:
            # Fallback for uninitialized state during unpickling
            return id(self)
