"""A set of index elements (X)"""

import logging
from operator import is_
from typing import Self

from IPython.display import Math, display

from .cases import ICase

logger = logging.getLogger("gana")

try:
    from pyomo.environ import RangeSet as PyoRangeSet
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
    """
    Set of index elements (X).

    :param members: Members of the Index set.
    :type members: str | int, optional
    :param size: Size of the Index set, creates an ordered set if given.
    :type size: int, optional
    :param mutable: If the Index set is mutable. Defaults to False.
    :type mutable: bool, optional
    :param tag: Tag/details. Defaults to None.
    :type tag: str, optional
    :param dummy: If the Index set is a dummy set, elements are created immediately. Defaults to False.
    :type dummy: bool, optional

    :ivar _: Elements of the index set
    :vartype _: list[X]
    :ivar tag: Tag/details
    :vartype tag: str
    :ivar ordered: Ordered set, True if size is given
    :vartype ordered: bool
    :ivar name: Name, set by the program
    :vartype name: str
    :ivar n: Number id, set by the program
    :vartype n: int
    :ivar ltx: LaTeX representation
    :vartype ltx: str

    :raises ValueError: If both members and size are given
    :raises ValueError: If indices of elements (P, V) are not compatible
    :raises ValueError: If index set is not ordered and step is given


    .. admonition:: Example

        .. code-block:: python

            p = Program()
            p.s1 = I('a', 'b', 'c')
            p.s2 = I('a', 'd', 'e', 'f')

            # Intersection
            p.s1 & p.s2
            # I('a')

            # Union
            p.s1 | p.s2
            # I('a', 'b', 'c', 'd', 'e', 'f')

            # Symmetric difference
            p.s1 ^ p.s2
            # I('b', 'c', 'd', 'e', 'f')

            # Difference
            p.s1 - p.s2
            # I('b', 'c')
    """

    def __init__(
        self,
        *members: str | int,
        size: int = None,
        mutable: bool = False,
        tag: str = None,
        ltx: str = None,
        dummy: bool = False,
    ):
        self.tag = tag
        self.mutable = mutable
        # set by program
        self.name = ""
        self.n = None

        # this is when children single element sets are created
        # These will be set in ._
        self.parent: list[Self] = []
        self.pos: list[int] = []
        self._: list[Self] = []

        # if it is a slice
        self.slice: slice = None

        # hash passed on along with name
        # self._hash = ''

        if size:
            if members:
                raise ValueError(
                    "An index set can either be defined by members or size, not both"
                )
            self.size = size
            self.members = []
            self.ordered = True

        elif members:
            self.size = len(members)
            self.members = members
            self.ordered = False

        else:
            self._ = []
            self.members = []
            self.ordered = False

        # # compound sets collect a list of children sets
        # # from which they are made
        # self.children: list[Self] = []
        # # These are used for index arrays for function (F) sets
        # self.one: I = None
        # self.two: I = None

        self.parameters = []
        self.variables = []
        self.functions = []
        self.constraints = []

        # if latex name is given
        self._ltx = ltx

        if dummy:
            self.case = ICase.DUMMY
            self.birth_elements()

        else:
            self.case: ICase = None

    def birth_elements(self):
        """Create elements for the index set"""
        # if self.ordered:
        self.size = int(self.size)
        for n in range(self.size):
            # this is called from outside
            # (once the name is set)
            # for an ordered index set
            # create new index
            index = I()
            # append parent
            index.parent.append(self)
            # update position in parent
            index.pos.append(n)
            # set that this is ordered
            index.ordered = True
            # give the name
            index.name = rf"{self}[{n}]"
            index._hash = hash(index.name)
            # the only element in element (index set of size one)
            # is itself
            index._ = [index]
            index.size = 1
            index.members = [index.name]
            self._.append(index)
            # index.ltx = r"{" + rf"{self.ltx}_{n}" + r"}"

    # -----------------------------------------------------
    #                    Modifiers
    # -----------------------------------------------------

    def step(self, n: int) -> list[Self]:
        """
        Step up or down the index set

        :param n: Step size
        :type n: int

        :returns: New index set stepped up or down
        :rtype: I
        """
        if not self.ordered:
            raise ValueError(
                "Index set is not ordered, cannot step up or down the index set"
            )
        if not n:
            # if no step (0)
            return self

        # else create a new index set
        index = I()
        # if step is negative
        if n < 0:
            in_index = self._[:n]
            index._ = [None] * -n + in_index
            # the negative sign will come with n
            index.name = f"{self.name}{n}"
        else:
            in_index = self._[n:]
            index._ = in_index + [None] * n
            # + needs to be provided
            index.name = f"{self.name}+{n}"

        # update the members
        index.members = [i.name for i in in_index]
        # note that this is a subset of self
        index.parent = self
        # the size is still the same
        index.size = self.size
        # only done for index set
        index.ordered = True
        # latex representation
        index._ltx = self.ltx

        return index

    # -----------------------------------------------------
    #                    Printing
    # -----------------------------------------------------
    @property
    def ltx(self) -> str:
        """LaTeX representation"""
        if self.ordered:
            # this is a true subset, a single index point
            # not a splice or a step
            if self.parent and isinstance(self.parent, list):
                self._ltx = r"{" + rf"{self.parent[0].ltx}_{self.pos[0]}" + r"}"
            elif not self._ltx:
                self._ltx = self.name.replace("_", r"\_")

        else:
            self._ltx = self.name.replace("_", r"\_")
        return r"{" + self._ltx + r"}"

    # def nsplit(self):
    #     """Split the name
    #     If there is an underscore, the name is split into name and superscript
    #     """
    #     if '_' in self.name:
    #         name, sup = self.name.split('_')
    #         if sup:
    #             return r'{' + name + r'}', r'^{' + sup + r'}'
    #         # this is used for negation sometimes
    #         return '-' + self.name[:-1], ''
    #     return r'{' + self.name + r'}'

    def latex(self, descriptive: bool = True, int_not: bool = False) -> str:
        """
        LaTeX representation

        :param descriptive: print members of the index set
        :type descriptive: bool, optional
        :param int_not: Whether to display the set in integer notation.
        :type int_not: bool, optional
        :returns: LaTeX representation of the index set
        :rtype: str
        """

        if not self.name:
            return ""

        # if self.parent and any(parent.ordered for parent in self.parent):
        #     ltx = ltx.replace("[", "_{").replace("]", "}")
        #     ltx = r"{" + ltx + r"}"

        # else:
        #     ltx = ltx.replace("[", "{").replace("]", "}")

        # name, sup = self.nsplit()
        # self.ltx = self.ltx
        # mathcal = rf'\mathcal{{{name}{sup}}}'

        if self.parent:
            return self.ltx

        if self.case == ICase.SELF:
            # if this is a self contained index
            return ""

        if descriptive:
            if self.ordered:
                if int_not:
                    return (
                        rf"\{{ i = \mathbb{{{self.ltx}}} \mid "
                        rf"{self._[0]} \leq i \leq {self._[-1]} \}}"
                    )
                members = (
                    r", ".join(x.latex() for x in self._)
                    if len(self) < 5
                    else rf"{self._[0].latex()},..,{self._[-1].latex()}"
                )
                return rf"{self.ltx} = \{{ {members} \}}"

            members = r", ".join(x.latex() for x in self._)
            return rf"{self.ltx} = \{{ {members} \}}"
        return self.ltx

    def show(self, descriptive: bool = True):
        """
        Display the set

        :param descriptive: Print members of the index set
        :type descriptive: bool, optional
        """
        display(Math(self.latex(descriptive)))

    def mps(self, pos: int) -> str:
        """
        MPS representation

        :param pos: Position of the member in the set
        :type pos: int

        :returns: MPS representation of the member at position pos
        :rtype: str
        """
        return rf"_{self[pos]}".upper()

    def lp(self, pos: int) -> str:
        """
        LP representation

        :param pos: Position of the member in the set
        :type pos: int
        """
        return rf"_{self[pos]}"

    # -----------------------------------------------------
    #                    Birth
    # -----------------------------------------------------

    def birth_index(self, name: str, members: list[Self]) -> Self:
        """
        Updates the parent, sets new positions and mutable/ordered attributes

        :param name: Name of the new index set
        :type name: str
        :param members: Members of the new index set
        :type members: list[I]

        :returns: New index set
        :rtype: I
        """
        # set new members for the index
        index = I()
        # set a name for the new index
        index.name = name
        # update the members of the index
        # doing this from outside avoids creating
        # element index sets (X) again
        index.members = members
        index.ordered = self.ordered
        return index

    # -----------------------------------------------------
    #                    Operators
    # -----------------------------------------------------

    # Avoid running instance checks
    def __eq__(self, other: Self):
        # equality checks for index sets are only done
        # on the basis of names
        return is_(self, other)

    def __and__(self, other: Self):
        # Members that exist in both Index sets
        _and = [i for i in self.members if i in other.members]

        return self.birth_index(rf"{self.name} & {other.name}", _and)

    def __or__(self, other: Self):
        # members that exist in either self or other
        # make a copy of the members in self
        _or = list(self.members)
        # if a member in other is not included
        for i in other.members:
            if i not in _or:
                # append it to the list
                _or.append(i)
        # mutable sets will have the same name
        # and are mutated using | (__or__)
        # repeated names are not allowed,
        # thus if the same name is coming in,
        # the index is definitely being mutated
        if self.name == other.name:
            return self.birth_index(self.name, _or)

        # else create a new name that reflects the operation
        return self.birth_index(rf"{self.name} | {other.name}", _or)

    def __xor__(self, other: Self):
        # members that exist in either self or other, but not both
        # create an empty list to be updated
        _xor: list[Self] = []
        # if something is in self but not in other
        for i in self.members:
            if i not in other.members:
                _xor.append(i)
        # if something is in other but not in self
        for i in other.members:
            if i not in self.members:
                _xor.append(i)
        return self.birth_index(rf"{self.name} ^ {other.name}", _xor)

    def __sub__(self, other: int | Self):
        # other is an integer, step down the index set
        if isinstance(other, int):
            if len(self) == 1:
                return
            return self.step(-other)

        # members from other are removed from self
        # if other is some type of an Index set
        # create an empty list
        _sub = []
        # if a member of self is in the other set
        for i in self.members:
            if i not in other.members:
                # do not append
                _sub.append(i)
        return self.birth_index(rf"{self.name} - {other.name}", _sub)

    def __add__(self, other: int | Self):
        # if other is an integer, step up the index set
        if isinstance(other, int):
            return self.step(other)

        raise NotImplementedError(
            'Addition of Index sets is not implemented. Use | or the "or" operator for union.\n'
            "+  can be used to step up the index set by an integer."
        )

    def __mul__(self, other: Self | tuple | None):
        # product of two Index sets

        if other is None:
            # This will likely be used mostly for element indices
            # allowing indices to be skipped while generating elements
            return None

        # if other is a tuple, return a tuple with self as the first element
        if isinstance(other, tuple):
            return (self,) + other

        # if other is an Index set, return a tuple of index sets
        return (self, other)

    def __rmul__(self, other: Self | tuple | None):
        if other is None:
            return None

        if isinstance(other, int):
            # This allows the use of math.prod
            if other == 1:
                return self

        # the only other allowed instance for which this
        # is called is tuple
        # Not running an instance check to save time
        return other + (self,)

    # -----------------------------------------------------
    #                    Vector
    # -----------------------------------------------------

    def __len__(self) -> int:
        return len(self._)
        # return len([i for i in self._ if not isinstance(i, Skip)])

    def __iter__(self) -> Self:
        return iter(self._)

    def __getitem__(self, key: int | str | slice) -> Self:
        if isinstance(key, slice):
            #  if this is a slice [start:stop]
            # generate a new index set for that stretch
            index = I(*self._[key], mutable=self.mutable, tag=self.tag)
            # mark this as a subset of self
            index.parent = self
            index.slice = key
            # note the start and stops
            if key.start is None:
                index.name = rf"{self.name}[0:{key.stop}]"
            else:
                index.name = rf"{self.name}[{key.start}:{key.stop}]"

            index.ordered = self.ordered
            index._ = self._[key]
            return index
        return self._[key]

    def __contains__(self, other: Self):
        return True if other in self._ else False

    # -----------------------------------------------------
    #                    Hashing
    # -----------------------------------------------------

    # __str__ = lambda self: self.name
    # __repr__ = __str__
    # __hash__ = lambda self: hash(self.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

    def __hash__(self):
        # this seems to work the fastest
        # not sure how pythonic this is though
        try:
            return self._hash

        except AttributeError:
            self._hash = hash(self.name)
            # self._hash = hash(self.name)
            return self.__hash__()

        # if not self._hash:
        #     self._hash = hash(self.name)

        # return self._hash

    # -----------------------------------------------------
    #                    Export
    # -----------------------------------------------------

    # def sympy(self):
    #     """Sympy representation"""
    #     if has_sympy:
    #         return FiniteSet(*[str(s) for s in self._])
    #     logger.warning(
    #         "⚠ sympy is an optional dependency, pip install gana[all] to get optional dependencies ⚠"
    #     )

    # def pyomo(self):
    #     """Pyomo representation"""
    #     if has_pyomo:
    #         if self.ordered:
    #             return PyoRangeSet(len(self), doc=self.tag)

    #         return PyoSet(initialize=[i.name for i in self._], doc=self.tag)
    #     logger.warning(
    #         "⚠ pyomo is an optional dependency, pip install gana[all] to get optional dependencies ⚠"
    #     )
