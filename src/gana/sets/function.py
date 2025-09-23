"""Function Set"""

from __future__ import annotations

from itertools import product
from typing import TYPE_CHECKING, Self

from .birth import make_P, make_T
from .cases import Elem, FCase, PCase
from .constraint import C
from .index import I

try:
    from IPython.display import Math, display

    has_ipython = True
except ImportError:
    has_ipython = False

if TYPE_CHECKING:
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
        one_type (Elem, optional): one' type. Default to None
        two_type (Elem, optional): two' type. Default to None
        mul (bool, optional): Multiplication. Defaults to False.
        add (bool, optional): Addition. Defaults to False.
        sub (bool, optional): Subtraction. Defaults to False.
        div (bool, optional): Division. Defaults to False.
        consistent (bool, optional): If the function is already consistent. Saves some computation. Defaults to False.
        case (FCase, optional): Special Function case. Defaults to None.
        parent (Self, optional): Parent function. Defaults to None.
        pos (int, optional): Position of the function in the parent. Defaults to None.
        index (tuple[I] | list[tuple[I]] | None, optional): Index of the function. Defaults to None.
        issumhow (tuple[V, I, int], optional): If the function is a summation, this is the variable, index and position of the summation. Defaults to None.
        process (bool, optional): whether to make matrices. Defaults to True
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
        struct tuple[Elem, Elem]: Structure of the function
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
        # --------- Elements -----------
        one: int | float | list[int | float] | P | V | T | Self | None = None,
        two: int | float | list[int | float] | P | V | T | Self | None = None,
        # --------- Types --------------
        one_type: Elem = None,
        two_type: Elem = None,
        # ------- Relations -----------
        mul: bool = False,
        add: bool = False,
        sub: bool = False,
        div: bool = False,
        # ------ Vector ---------------
        parent: Self = None,
        pos: int = None,
        index: tuple[I] | list[tuple[I]] | None = None,
        # ------- Other attributes -----
        case: FCase = None,
        consistent: bool = False,
        issumhow: tuple[V, I, int] = None,
    ):
        # set by program or birther function (parent)
        self.parent: Self = parent
        # position of the function in the parent
        self.pos: int = pos
        # number id, set by the program based on order of declaration
        self.n: int = None
        # members of the function set
        self._: list[F] = []
        # maps indices to functions in the set
        self.map = {}
        self.index = index
        # special function cases
        self.case = case
        self.consistent = consistent

        # this gives you (variable, list of indices, set to sum, pos of set to sum)
        self.issumhow = issumhow

        # evaluates the value of the function
        self.X: {int, float} = {}

        # calculated variable
        self.calculation: V = None

        # category of the constraint
        # constraints can be printed by category
        self.category: str = ''

        self._matrix: dict = {}

        if self.issumhow:

            #     self.one =

            self.mis = 0
            self._one = one._
            self._two = two._
            self.one = one
            self.two = two
            self.index = one.index + (two.index,)

            self.handle_rel(mul, add, sub, div, ignore=True)

            self.one_type = Elem.F
            self.two_type = Elem.V
            self.make_args()
            self._ = []
            self.n = 0
            self.name, self.pname = '', ''
            self.A, self.P, self.Y, self.Z, self.B, self.F = ([] for _ in range(6))
            self.variables = []

        elif one is not None or two is not None:
            # A basic Function is of the type
            # P*V, V + P, V - P
            # P can be a number (int or float), parameter set (P) or list[int | float]
            # for multiplication P comes before variable

            one, two = self.types(one, one_type, two, two_type)

            if not self.consistent:
                # internal operations are made to adhere to the consistent form
                # this is notified to avoid doing this operation
                # saves time and computational resources
                one, one_type, two, two_type, add, sub, mul, div = self.make_consistent(
                    one, one_type, two, two_type, add, sub, mul, div
                )

            # now that the function is consistent
            # set one and two

            self.one = one()
            self.two = two()

            # if the entirety of self is being returned on call
            # this prevents the entirety of self being an element of a function
            # as variables can mutate in gana
            if self.one_type == Elem.V and self.one.make_copy:
                self.one = self.one.copy()

            if self.two_type == Elem.V and self.two.make_copy:
                self.two = self.two.copy()

            # check the mismatch
            # and rectify it if necessary
            # all iterations in the function will be done using _one and _two
            self.handle_mismatch()

            # fix the relational attributes
            self.handle_rel(mul, add, sub, div)

            if not self.index:
                # update the index
                self.handle_index()

            self.make_args()

            # self.give_name()

            # donot birth for birthed functions
            if self.parent is None:
                # needs the mismatch to generate matrices
                self.generate_matrices()
                # matrix is passed on to the birthed functions
                self.birth_functions()
                # make a matrix of positions
                self.P = [f.P for f in self._ if f is not None]

            else:
                self.update_variables()

                # self.variables = [
                #     v(*i) for v, i in zip(self.parent.variables, self.index)
                # ]
        else:
            # if an empty function is created, attributes still need to be set
            # empty functions are used when doing operations outside
            # is more efficient computationally
            # this is especially true when the final structure is known
            # sum(variable_{i}) for example, where
            # instead of adding the function recursively, the final structure can be passed

            self.mis = 0
            self._one = []
            self._two = []
            self.one = one
            self.two = two
            self.index = None

            self.handle_rel(mul, add, sub, div, ignore=True)
            self.one_type = one_type
            self.two_type = two_type
            self.make_args()
            self._ = []
            self.n = 0
            self.name, self.pname = '', ''
            self.A, self.P, self.Y, self.Z, self.B, self.F = ([] for _ in range(6))
            self.variables = []

        self.give_name()

    @property
    def matrix(self) -> dict:
        """Matrix as dict
        Returns:
            dict: Dictionary mapping of positions to values in A matrix

        """
        if self._matrix:
            return self._matrix

        if self.parent is not None:
            self._matrix = dict(zip(self.P, self.A))
        else:
            self._matrix = {f: f.matrix for f in self._}

        return self._matrix

    @property
    def struct(self) -> tuple[Elem, Elem]:
        """Structure of the function

        Returns:
            tuple[Elem, Elem]: Structure of the function
        """
        return (self.one_type, self.two_type)

    @property
    def elements(self) -> list[P | V | T | Self]:
        """Elements in the function

        Returns:
            list[P | V | T | Self]: Elements in the function
        """
        return (
            self.variables + self.mul_parameters + self.rhs_parameters + self.rhs_thetas
        )

    @property
    def index_flat(self) -> list[int]:
        """Flattens the index of the function

        Returns:
            list[int]: Flattened index of the function
        """
        return (
            [v.index for v in self.variables]
            + [p.index for p in self.mul_parameters]
            + [r.index for r in self.rhs_parameters]
            + [t.index for t in self.rhs_thetas]
        )

    # -----------------------------------------------------
    #                    Helpers
    # -----------------------------------------------------

    def categorize(self, category: str):
        """Categorizes the function"""
        self.category = category
        for c in self._:
            c.category = category

    def make_consistent(
        self,
        one: V | P | T | Self,
        one_type: Elem | None,
        two: V | P | T | Self,
        two_type: Elem | None,
        add: bool,
        sub: bool,
        mul: bool,
        div: bool,
    ) -> tuple[V | P | T | Self, Elem, V | P | T | Self, Elem, bool, bool, bool | bool]:
        """Sets the function in a consistent form

        Also makes parameters from int, float, or list[int|float] if needed

        sets self.isconsistent to True
        """
        # make consistent
        self.isconsistent = True

        # basically, keep variables (or function) to the left for add and sub
        # if function involves a parameters and variable or function
        # for multiplication keep variable (or function) on the right (P*V|F)
        if (add and one_type in [Elem.P, Elem.T]) or (
            mul and two_type in [Elem.P, Elem.T]
        ):
            # for addition, always keep V|F + P
            # for multiplication, always keep P * V|F
            return two, two_type, one, one_type, add, sub, mul, div

        elif sub and one_type in [Elem.P, Elem.T]:
            # for subtraction, always keep -V + P
            add = True
            sub = False
            one_type, two_type = two_type, one_type
            return -two, two_type, one, one_type, add, sub, mul, div

        elif div and two_type == Elem.P:
            div = False
            mul = True
            one_type, two_type = two_type, one_type
            return 1 / two, two_type, one, one_type, add, sub, mul, div

        return one, one_type, two, two_type, add, sub, mul, div

    def handle_mismatch(self):
        """Determine mismatch between indices

        Stretches the shorter index to match the longer one.

        This comes up in writing 'multiscale' constraints, e.g.:
        ..math::
            \\mathbf{production}_{operation, hour} - \\mathrm{Parameter}_{operation, time} \\cdot \\mathbf{capacity}_{operation, year} \\leq 0

        One of the indices needs to be divisible by the other if there is a mismatch

        Sets self.mis, self._one, self._two, self.one, self.two
        """

        if self.parent is None and (self.one and self.two):

            # only applies for non birthed functions
            lone = len(self.one)
            ltwo = len(self.two)

            # check the compatibility
            if not lone % ltwo == 0 and not ltwo % lone == 0:
                raise ValueError(
                    f'{self.one} with index {self.one.index} (length = {lone}) and {self.two} with {self.two.index} (length = {ltwo}) are not compatible'
                )
            if lone > ltwo:
                # one is longer, keep as is
                # negative informs that one is longer
                self.mis = -int(lone / ltwo)
                self._one, self._one_map = self.one._, self.one.map
                # stretch two

                self._two = [x for x in self.two._ for _ in range(-self.mis)]
                self._two_map = [i for i in self.two.map for _ in range(-self.mis)]
                # self._two_map = (
                #     self.one.map
                # )  # [i for i in self.two.map for _ in range(-self.mis)]

            elif ltwo > lone:
                # two is longer, keep as is
                # positive informs that two is longer
                self.mis = int(ltwo / lone)

                # stretch one
                self._one = [x for x in self.one._ for _ in range(self.mis)]
                self._one_map = [i for i in self.one.map for _ in range(self.mis)]
                self._two, self._two_map = self.two._, self.two.map

            else:
                self.mis = 0
                self._one, self._one_map = self.one._, self.one.map
                self._two, self._two_map = self.two._, self.two.map

        else:
            # for birthed functions, there is never a mismatch
            # moreover, the variables are passed on from the parent

            self.mis = 0

            # this handles both P and the rest
            self._one, self._two = [self.one], [self.two]

            # parameters will be passing floats and ints
            if isinstance(self.one, (int, float)) or self.one is None:
                self._one_map = self.two.map
            else:
                self._one_map = self.one.map

            if isinstance(self.two, (int, float)) or self.two is None:
                self._two_map = self.one.map
            else:
                self._two_map = self.two.map

    def handle_index(self):
        """Handles (compounds if needed) the index
        Irrespective of the operation being done

        The index of a function is index.one + index.two
        Not in the mathematical sense!
        i am just using the __add__ dunder for I to create
        a function index basically.
        This is of the form
        ..math::
            f(\\mathbf{x}, \\mathbf{y})_{i,j} = \\mathbf{x}_{i} + \\mathbf{y}_{j}

        sets self.index
        """

        # index is a combination of one and two
        index: tuple[tuple[I]] = []

        # update the index
        if self.one_type == Elem.F:
            index += self.one.index
        else:
            # elif self.one_type in [Elem.V, Elem.T, Elem.P]:

            index += (self.one.index,)

        if self.two_type == Elem.F:
            index += self.two.index
        else:
            # if self.two_type in [Elem.V, Elem.T, Elem.P]:
            index += (self.two.index,)

        self.index = tuple(index)

    def handle_rel(
        self, mul: bool, add: bool, sub: bool, div: bool, ignore: bool = False
    ):
        """Handles the relation of the function
        sets self.args, self.mul, self.add, self.sub, self.div, self.rel
        """
        # rel is used for printing
        # For the purpose of operations signs are explicit bools

        self.mul = mul
        self.add = add
        self.sub = sub
        self.div = div

        # rel looks good for printing
        # one rel two
        if self.mul:
            self.rel = '×'
        elif self.add:
            self.rel = '+'
        elif self.sub:
            self.rel = '-'
        elif self.div:
            self.rel = '÷'
        else:
            if not ignore:
                # if no operation is specified, raise an error
                # this is to avoid confusion
                # if you want to create a function without an operation, use F()
                raise ValueError('one of mul, add, sub or div must be True')

    def make_args(self):
        """Makes the arguments for the function
        This is convenient for passing to the birther functions
        and while making calls to the function.
        Also sets self.args
        """
        # these are passed on for mutation or birthing
        self.args = {
            'one_type': self.one_type,
            'two_type': self.two_type,
            'mul': self.mul,
            'add': self.add,
            'sub': self.sub,
            'div': self.div,
            'consistent': self.consistent,
            'case': self.case,
        }

    def birth_functions(self):
        """Creates a vector of functions
        Accordingly sets n
        sets self._, self.n
        """

        # _one and _two are used because
        # they are created post handling an length mismatches
        for n, (one, one_idx, two, two_idx) in enumerate(
            zip(self._one, self._one_map, self._two, self._two_map)
        ):
            # only update the indices for F and V for functions
            index: tuple[tuple[I]] = []

            if self.one_type == Elem.F:
                index += one_idx

            else:

                # if self.one_type == Elem.V:
                index += (one_idx,)

            if two is None:
                # you can have just a P or T masquerading as a function
                # so check are unnecessary
                # f = one(*one.index)

                index = tuple(index)

                if isinstance(one, (int, float)):
                    # this happens when there is a skipped index
                    self.map[index] = None
                    self._.append(None)
                    continue
                else:
                    f = one()
                    f.map[index] = f

            else:
                # this is done to handle skipping
                #  for shifted indices (.step)
                if self.two_type == Elem.F:
                    index += two_idx

                else:
                    index += (two_idx,)

                index = tuple(index)

                f = F()
                f.parent = self
                f.index = index

                if one:
                    if self.one_type in [Elem.P, Elem.T]:
                        f.one = one
                    else:

                        f.one = one(*one_idx)

                if self.two_type in [Elem.P, Elem.T]:
                    f.two = two
                else:
                    f.two = two(*two_idx)

                f.pos = n
                f.one_type, f.two_type = self.one_type, self.two_type
                f.mul, f.add, f.sub, f.div = self.mul, self.add, self.sub, self.div
                f.rel = self.rel
                f.consistent = self.consistent
                f.case = self.case
                f.issumhow = self.issumhow

                f.update_variables()
                f.give_name()
                f.map[one_idx, two_idx] = f
                f.A = self.A[n]
                f.B = self.B[n]

            # update the map
            self.map[index] = f

            # only member of the birthed function is itself
            f._ = [f]
            # populate the set
            self._.append(f)

    def update_variables(self):
        """Updates the variables in the function"""
        self.variables: list[V] = []

        if self.one_type == Elem.F:
            # if function, extend the lists
            self.variables.extend(self.one.variables)
        elif self.one_type == Elem.V:
            # if variable, append the variable
            self.variables.append(self.one)

        if self.two_type == Elem.F:
            self.variables.extend(self.two.variables)

        elif self.two_type == Elem.V:
            self.variables.append(self.two)

        # make a matrix of positions of the variables
        self.P = [v.n for v in self.variables if v is not None]

    def give_name(self):
        """Gives a name to the function"""

        # set by program
        self.pname: str = ''

        if self.case == FCase.SUM:
            variable, over, _ = self.issumhow

            self.name = f'sigma({variable}({variable.index}),{over})'
        # elif self.case == FCase.NEGSUM:
        #     self.name = f'-sigma({self.variables[0].parent}[{self.variables[0].pos}:{self.variables[-1].pos}])'
        else:
            _name = ''
            if self.one is not None:
                _name += str(self.one)
            if self.two is not None:
                _name += f'{self.rel}{self.two}'

            self.name = _name

    def types(
        self,
        one: V | P | T | Self,
        one_type: Elem | None,
        two: V | P | T | Self,
        two_type: Elem | None,
    ) -> tuple[V | P | T | Self, V | P | T | Self]:
        """Sets whether there is an element of a particular type
        in one and two

        Args:
            one_type (Elem | None): Type of the first element
            two_type (Elem | None): Type of the second element

        sets self.one_type, self.two_type
        """
        # this is meant to be avoided as far as possible
        # look at how the operations for each element is defined
        # to some extent it is difficult to avoid some sort of instance check
        # but if there is an instance check happening prior to the operation
        # it is better to pass the type directly
        # every instance check is time consumed, so at the least
        # avoid multiple instance checks for the same element

        def check_type(elem: P | V | T | Self):
            from .parameter import P
            from .theta import T
            from .variable import V

            if isinstance(elem, V):
                return Elem.V
            if isinstance(elem, P):
                return Elem.P
            if isinstance(elem, T):
                return Elem.T
            if isinstance(elem, F):
                return Elem.F

        if not one_type:
            # If one type is not known
            # perform instance check
            one_type = check_type(one)

        if not two_type:
            two_type = check_type(two)

        self.one_type = one_type
        self.two_type = two_type

        return one, two

    def generate_matrices(self):
        """Generates matrices
        A - variable coefficients
        X - position of continuous variables in program
        Y - position of discrete variables in program
        Z - position of parametric variables in program
        B - rhs parameters
        F - pvar (theta) parameters

        The general for is:
        ..math::
            \\mathrm{A} \\cdot \\mathbf{V} = \\mathrm{B} + \\mathrm{F} \\cdot θ

        sets self.A, self.P, self.Y, self.Z, self.B, self.F

        """

        # TODO, pass this on for birthed functions
        self.variables: list[V] = []
        self.rhs_parameters: list[P] = []
        self.mul_parameters: list[P] = []
        self.rhs_thetas: list[T] = []

        # theta parameter multipliers
        self.F = []
        # theta parameter positions
        self.Z = []

        # The following are a list of cases:
        # Base cases:
        # V + P (parameter is always on the right)
        # V - P (parameter is always on the right)
        # P*V (parameter is always on the left)
        # Function cases
        # F + P (parameter is computed in total and pushed to the right)
        # F - P (parameter is computed in total and pushed to the right)
        # Compound cases:
        # V + F (both have A, two has B)
        # V - F (both have A, two has B)
        # V*F (not implemented yet)

        # these (SUM, NEGSUM) are just boxes
        # if self.case == FCase.SUM:
        #     # all positive
        #     self.A = [[1] * len(self.index)] * len(self.index)
        #     self.B = [0] * len(self.index)

        # elif self.case == FCase.NEGSUM:
        #     # all negative
        #     self.A = [[-1] * len(self.index)] * len(self.index)
        #     self.B = [0] * len(self.index)

        # else:
        # update the elements in the function
        if self.one_type == Elem.F:
            # two can be F, V, P, or T

            self.variables.extend(self.one.variables)
            # irrespective, we only need to take A here
            if self.mis > 0:
                # if there is a mismatch,
                # positive indicates that two is longer
                # so scale the A to match
                self.A = [row[:] for _ in range(self.mis) for row in self.one.A]
            else:
                self.A = self.one.A

        elif self.one_type == Elem.V:
            # two can be F, V, P, or T
            self.variables.append(self.one)
            # irrespective, we only need to take A here
            if self.mis > 0:
                # if there is a mismatch,
                # positive indicates that two is longer
                # so scale the A to match
                self.A = [row[:] for _ in range(self.mis) for row in self.one.A]
            else:
                self.A = self.one.A

        elif self.one_type == Elem.T:
            # TODO Bilevel: this is only possible for multiplication of variable/function with theta
            pass

        elif self.one_type == Elem.P:
            # this is only possible if mul is True
            # and two is V
            self.mul_parameters.append(self.one)
            if self.mul:
                if self.two_type == Elem.F and self.two.case == FCase.SUM:
                    if self.two.parent is not None:
                        self.A = [self.one._[n] * i for n, i in enumerate(self.two.A)]
                    else:
                        self.A = [
                            [self.one._[n] * i for i in j]
                            for n, j in enumerate(self.two.A)
                        ]
                else:
                    # so you A is a the parameter matrix
                    # self.A = self.one.A
                    if self.mis > 0:
                        # if there is a mismatch,
                        # positive indicates that two is longer
                        self.A = [row[:] for _ in range(self.mis) for row in self.one.A]
                    else:
                        self.A = self.one.A

                # at this point, it can be of the type P*(V|F)
                # if F = V +- P, we use the operation P*V +- P*P
                # so P always shows up at two
                # if this is just of the form (P*V) or (P*F) where F = P*V
                # B will not be set if self.two_type is not P
                # it is just safe to set a B here, if needed it will be overwritten
                if self.mis > 0:
                    # if there is a mismatch,
                    # positive indicates that two is longer
                    # make a B of length of two
                    self.B = [0] * len(self._two)
                else:
                    # if one is longer
                    # or there is no mismatch (either one or two will do)
                    self.B = [0] * len(self._one)

        # update the elements in the function
        if self.two_type == Elem.F:
            # one could have been a V, T, or F
            self.variables.extend(self.two.variables)
            if self.one_type in [Elem.F, Elem.V]:
                # if V or F, A definitely exists, so update A
                if self.mis < 0:
                    # if there is a mismatch,
                    # negative indicates that one is longer
                    # scale two's A to correct mismatch
                    _A = [row[:] for _ in range(-self.mis) for row in self.two.A]

                else:
                    _A = self.two.A
                if self.add:
                    self.A = [a + b for a, b in zip(self.A, _A)]
                if self.sub:
                    self.A = [a + [-bb for bb in b] for a, b in zip(self.A, _A)]

        elif self.two_type == Elem.V:
            # one could have been a V, T, or F
            self.variables.append(self.two)

            if self.one_type in [Elem.F, Elem.V]:
                # if V or F, A definitely exists, so update A
                if self.mis < 0:
                    # if there is a mismatch,
                    # negative indicates that one is longer
                    # scale two's A to correct mismatch
                    _A = [row[:] for _ in range(-self.mis) for row in self.two.A]
                else:
                    _A = self.two.A

                if self.add:

                    self.A = [a + b for a, b in zip(self.A, _A)]

                if self.sub:
                    self.A = [a + [-bb for bb in b] for a, b in zip(self.A, _A)]

        elif self.two_type == Elem.T:
            # if self.one_type == Elem.F and self.one.two_type == Elem.T:
            #     if self.add:
            #         self.F = [i + [-1] for i in self.one.F]
            #     if self.sub:
            #         self.F = [i + [1] for i in self.one.F]
            # else:
            #     if self.add:
            #         self.F = [[-1]] * len(self._one)
            #     if self.sub:
            #         self.F = [[1]] * len(self._one)
            self.rhs_thetas.append(self.two)

        if self.two_type == Elem.P:

            # this is only possible for addition and subtraction
            if self.add:
                self.rhs_parameters.append(self.two)
                # if addition, since B is rhs, negate
                if self.mis < 0:
                    # if there is a mismatch,
                    # negative indicates that one is longer
                    # so scale the parameter to match
                    self.B = [-b for b in self.two._] * (-self.mis)
                else:
                    self.B = [-b for b in self.two._]
            elif self.sub:
                self.rhs_parameters.append(self.two)
                # if subtraction, since B is rhs, keep as is
                if self.mis < 0:
                    # if there is a mismatch,
                    # negative indicates that one is longer
                    # so scale the parameter to match
                    self.B = self.two._ * (-self.mis)
                else:
                    self.B = self.two._

        else:
            # if not caught by the parameter check
            # set a B of zeros
            self.B = [0] * len(self.A)

    # -----------------------------------------------------
    #                    Printing
    # -----------------------------------------------------

    def latex(self) -> str:
        """LaTeX Equation"""

        if self.case == FCase.CALC:
            # if this is a calculated variable
            if self.calculation.case == FCase.SUM:
                # self.case = FCase.SUM
                # two_ = self.latex()
                # self.case = FCase.CALC
                self.case = FCase.SUM
                two = self.latex()
                self.case = FCase.CALC
                return rf'{self.calculation.latex()} = {two}'

            if self.one_type == Elem.P and self.parent:
                # if this is a child function with a parameter
                # one will int/float
                one = self.one
            else:
                one = self.one.latex()

            return rf'{self.calculation.latex()} = {one} \cdot {self.two.latex()}'

        if self.case == FCase.FVAR:
            # if this is a variable being treated as a function
            return self.two.latex()

        if self.case in [FCase.SUM, FCase.NEGSUM]:
            # if this is a summation

            v, over, pos = self.issumhow
            # the position of the index over which it is being summed is passed by sigma

            # use i for summed index
            index = [
                'i' if n == pos else str(i).replace('[', '').replace(']', '')
                for n, i in enumerate(v.index)
            ]
            index = ', '.join(index)

            if v.ltx:
                oneissum = v.ltx
            else:
                oneissum = v.name

            ltx = rf'\sum_{{i \in {over}}} {oneissum}_{{{index}}}'

            if self.case == FCase.NEGSUM:
                # if this is a summation
                # return the summation
                return rf'-{ltx}'
            return rf'{ltx}'

        if self.one is None and self.mul:

            one = '0'

        elif self.one is not None:
            # _one = self.one(self.index.one)
            if self.one_type == Elem.P and self.parent:
                # if this is a child function with a parameter
                # one will int/float
                one = self.one
            else:
                one = self.one.latex()

        else:
            one = ''

        if self.two is not None:
            # _two = self.two(self.index.two)
            if self.two_type == Elem.P and self.parent:
                # if this is a child function with a parameter
                # two will int/float
                two = self.two
            else:
                two = self.two.latex()
        else:
            two = None

        if two is None:
            return rf'{one}'

        if one is None:
            return rf'{two}'

        if self.add:
            return rf'{one} + {two}'

        if self.sub:
            if (
                self.one_type == Elem.F
                and self.one.struct != (Elem.P, Elem.V)
                and self.two_type == Elem.F
                and self.two.struct != (Elem.P, Elem.V)
                and not self.two.case == FCase.SUM
            ):
                # bracket are important for function minuses
                # alternatively, the entire function can be negated
                return rf'({one}) - ({two})'
            if (
                self.two_type == Elem.F
                and self.two.struct != (Elem.P, Elem.V)
                and not self.two.case == FCase.SUM
            ):

                return rf'{one} - ({two})'
            return rf'{one} - {two}'

        if self.mul:
            # handling special case where something is multiplied by -1
            if self.case == FCase.NEGVAR:
                # if self.one and self.one.isnum and self.one[0] in [-1, -1.0]:
                return rf'-{two}'
            if self.one_type == Elem.F:
                # if one is a function, it should be bracketed
                return rf'({one}) \cdot {two}'
            if self.two_type == Elem.F:
                # if two is a function, it should be bracketed
                return rf'{one} \cdot ({two})'
            if self.one_type == Elem.F and self.two_type == Elem.F:
                # if both are functions, they should be bracketed
                return rf'({one}) \cdot ({two})'

            return rf'{one} \cdot {two}'

        if self.div:
            # not the most developed gana operation, yet
            return rf'\frac{{{one}}}{{{two}}}'

    def show(self, descriptive: bool = False):
        """Display the function"""
        if has_ipython:
            if descriptive:
                for f in self._:
                    display(Math(rf'[{f.n}]' + r'\text{   }' + f.latex()))
            else:
                display(Math(rf'[{self.n}]' + r'\text{   }' + self.latex()))
        else:
            print(
                'IPython is an optional dependency, pip install gana[all] to get optional dependencies'
            )

    @property
    def longname(self):
        """Gives a longer more descriptive name for the function"""
        _name = ''
        if self.one is not None:
            if isinstance(self.one, (int, float)):
                _name += str(self.one)
            else:
                _name += self.one.longname
        if self.two is not None:
            if isinstance(self.two, (int, float)):
                _name += f'{self.rel}{self.two}'
            else:
                _name += f'{self.rel}{self.two.longname}'
        return _name

    # -----------------------------------------------------
    #                    Operators
    # -----------------------------------------------------

    def __neg__(self):

        if self.case == FCase.NEGVAR:
            # if function is a negated variable
            # return the variable
            return self.two

        if self.one_type == Elem.V:
            # negative of variable is -1*v
            # which is a function
            one_type = Elem.F

        else:
            one_type = self.one_type

        if self.case == FCase.SUM:
            # -(E1 + ... + En) = -E1 - ... - En
            # create and return a negative summation
            return

        if self.add:

            return F(
                # -(E1 + E2) = -E1 - E2
                one=-self.one,
                sub=True,
                two=self.two,
                one_type=one_type,
                two_type=self.two_type,
            )

        if self.sub:
            # -(E1 - E2) = -E1 + E2
            return F(
                one=-self.one,
                add=True,
                two=self.two,
                one_type=one_type,
                two_type=self.two_type,
            )

        if self.mul:
            # -(E1 * E2) = -E1 * E2
            return F(
                one=-self.one,
                mul=True,
                two=self.two,
                one_type=one_type,
                two_type=self.two_type,
            )
        if self.div:
            # -(E1 / E2) = -E1 / E2
            return F(
                one=-self.one,
                div=True,
                two=self.two,
                one_type=one_type,
                two_type=self.two_type,
            )

    def __pos__(self):
        return self

    def __add__(
        self,
        other: (
            V
            | P
            | T
            | Self
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> Self:
        from .parameter import P

        # F + None = F
        if other is None:
            # if adding with nothing, return itself
            return self

        if isinstance(other, (int, float)):
            # if adding with a number
            # F + 0 = F
            if other in [0, 0.0]:
                # if adding with 0, return self
                return self

            if self.two_type == Elem.P:
                if self.add:
                    # of the type, (V | F + P) + P
                    return F(
                        one=self.one,
                        add=True,
                        two=self.two + make_P(other, index=self.two.index),
                        one_type=self.one_type,
                        two_type=Elem.P,
                        consistent=True,
                    )
                if self.sub:
                    # of the type, (V | F - P1) + P2
                    # add if P2 > P1
                    two = make_P(other, index=self.two.index) - self.two

                    if two == 0:
                        # if equal to zero, return one
                        return self.one

                    if self.two.case in [PCase.NEGNUM, PCase.NUM]:
                        # if subtracting a number from a parameter
                        # return the parameter
                        if two._[0] < 0:
                            # this is leading to a negative parameter
                            return F(
                                one=self.one,
                                sub=True,
                                two=two,
                                one_type=self.one_type,
                                two_type=Elem.P,
                                consistent=True,
                            )
            if other < 0:

                return F(
                    one=self,
                    sub=True,
                    two=make_P(other, index=self.two.index),
                    one_type=Elem.F,
                    two_type=Elem.P,
                    consistent=True,
                )

            return F(
                one=self,
                add=True,
                two=make_P(other, index=self.two.index),
                one_type=Elem.F,
                two_type=Elem.P,
                consistent=True,
            )

        if isinstance(other, tuple):
            # if adding with a tuple
            # this is a theta
            other = make_T(other, index=self.one.index)

        if isinstance(other, list):
            # check 0th to see if tuple
            if isinstance(other[0], tuple):
                # if adding with a list of tuples
                # this is a theta
                other = make_T(other)
                return F(
                    one=self, add=True, two=other, one_type=Elem.F, two_type=Elem.T
                )

            if self.two_type == Elem.P:
                if self.add:
                    # of the type, V | F + P + P
                    return F(
                        one=self.one,
                        add=True,
                        two=self.two + make_P(other),
                        one_type=self.one_type,
                        two_type=Elem.P,
                        consistent=True,
                    )
                if self.sub:
                    # of the type, V | F - P + P
                    return F(
                        one=self.one,
                        sub=True,
                        two=make_P(other) - self.two,
                        one_type=self.one_type,
                        two_type=Elem.P,
                        consistent=True,
                    )

            return F(
                one=self,
                add=True,
                two=make_P(other),
                one_type=Elem.F,
                two_type=Elem.P,
            )

        if isinstance(other, P):
            # if adding with a parameter
            if self.two_type == Elem.P:
                if self.add:
                    # of the type, V | F + P1 + P2
                    return F(
                        one=self.one,
                        add=True,
                        two=self.two + other,
                        one_type=self.one_type,
                        two_type=Elem.P,
                        consistent=True,
                    )
                if self.sub:
                    # of the type, V | F - P + P
                    return F(
                        one=self.one,
                        sub=True,
                        two=other - self.two,
                        one_type=self.one_type,
                        two_type=Elem.P,
                        consistent=True,
                    )

        # these are of the type
        # F + P where F can be P*V or V/P

        if isinstance(other, F):
            return F(one=self, add=True, two=other, one_type=Elem.F, two_type=Elem.F)

        return F(one=self, add=True, two=other, one_type=Elem.F, issumhow=self.issumhow)

    def __radd__(
        self,
        other: (
            V
            | P
            | T
            | Self
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> Self:
        return self + other

    def __sub__(
        self,
        other: (
            V
            | P
            | T
            | Self
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> Self:
        from .parameter import P

        if other is None:
            # if subtracting with nothing, return itself
            return self

        if isinstance(other, (int, float)):
            # if substracting with a number
            if other in [0, 0.0]:
                # if subtracting with 0, return self
                return self

            if self.two_type == Elem.P:
                if self.add:
                    # of the type, V | F + P + P
                    two = self.two - make_P(other, index=self.two.index)
                    if two.case in [PCase.NUM, PCase.NEGNUM]:
                        if two > 0:
                            # if self.two - other is positive
                            return F(
                                one=self.one,
                                add=True,
                                two=two,
                                one_type=self.one_type,
                                two_type=Elem.P,
                                consistent=True,
                            )
                        if two < 0:
                            # if self.two - other is negative
                            return F(
                                one=self.one,
                                sub=True,
                                two=-two,
                                one_type=self.one_type,
                                two_type=Elem.P,
                                consistent=True,
                            )
                        else:
                            # if they are equal only self.one remains
                            return self.one
                    else:
                        # if self.two - other is not a number
                        return F(
                            one=self.one,
                            add=True,
                            two=two - make_P(other, index=self.two.index),
                            one_type=self.one_type,
                            two_type=Elem.P,
                            consistent=True,
                        )

                if self.sub:
                    # for substraction # of the type, V | F - P - P := V | F - (P + P)
                    return F(
                        one=self.one,
                        sub=True,
                        two=two + make_P(other, index=self.two.index),
                        one_type=self.one_type,
                        two_type=Elem.P,
                        consistent=True,
                    )

            if not self.two:
                index = self.one.index
            elif not self.one:
                index = self.two.index
            else:
                if self.two and self.one and len(self.two) > len(self.one):
                    index = self.two.index
                else:
                    index = self.one.index

            return F(
                one=self,
                sub=True,
                two=make_P(other, index=index),
                one_type=Elem.F,
                two_type=Elem.P,
                consistent=True,
            )

        if isinstance(other, tuple):
            # if subtracting with a tuple
            # this is a theta
            other = make_T(other, index=self.one.index)

        if isinstance(other, list):
            # check 0th to see if tuple
            if isinstance(other[0], tuple):
                # if subtracting with a list of tuples
                # this is a theta
                other = make_T(other)
                return F(
                    one=self, sub=True, two=other, one_type=Elem.F, two_type=Elem.T
                )
            if self.two_type == Elem.P:
                if self.add:
                    # of the type, V | F + P + P
                    return F(
                        one=self.one,
                        add=True,
                        two=self.two + make_P(other),
                        one_type=self.one_type,
                        two_type=Elem.P,
                        consistent=True,
                    )
                if self.sub:
                    # of the type, V | F - P + P
                    return F(
                        one=self.one,
                        sub=True,
                        two=make_P(other) - self.two,
                        one_type=self.one_type,
                        two_type=Elem.P,
                        consistent=True,
                    )

            return F(
                one=self,
                sub=True,
                two=make_P(other),
                one_type=Elem.F,
                two_type=Elem.P,
                consistent=True,
            )

        if isinstance(other, P):
            # if subtracting with a parameter
            if self.two_type == Elem.P:
                if self.add:
                    two = self.two - other
                    if two.case in [PCase.NUM, PCase.NEGNUM]:
                        # of the type, V | F + P1 - P2 := V | F + P3
                        if two > 0:
                            return F(
                                one=self.one,
                                add=True,
                                two=two,
                                one_type=self.one_type,
                                two_type=Elem.P,
                                consistent=True,
                            )
                        elif two < 0:
                            # of the type, V | F + P1 - P2:= V | F - P3
                            return F(
                                one=self.one,
                                sub=True,
                                two=-two,
                                one_type=self.one_type,
                                two_type=Elem.P,
                                consistent=True,
                            )
                    else:
                        return F(
                            one=self.one,
                            add=True,
                            two=self.two + other,
                            one_type=self.one_type,
                            two_type=Elem.P,
                            consistent=True,
                        )
                if self.sub:
                    # of the type, V | F - (P + P)
                    return F(
                        one=self.one,
                        sub=True,
                        two=self.two + other,
                        one_type=self.one_type,
                        two_type=Elem.P,
                        consistent=True,
                    )
        if isinstance(other, F):
            return F(one=self, sub=True, two=other, one_type=Elem.F, two_type=Elem.F)

        return F(one=self, sub=True, two=other, one_type=Elem.F, issumhow=self.issumhow)

    def __rsub__(
        self,
        other: (
            V
            | P
            | T
            | Self
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> Self:
        return -self + other

    def __mul__(
        self,
        other: (
            V
            | P
            | T
            | Self
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> Self:
        from .theta import T
        from .variable import V

        if other is None:
            # multiplying by nothing
            return None

        if isinstance(other, (int, float)):
            if other in [0, 0.0]:
                # multiplying by 0
                return 0

            if other in [1, 1.0]:
                # multiplying by 1
                return self

            # make a numeric parameter
            if self.case == FCase.SUM:
                one = make_P([other] * len(self))
                one.index = self.index
                return F(
                    one=one,
                    mul=True,
                    two=self,
                    one_type=Elem.P,
                    two_type=Elem.F,
                )

            two = make_P(other, index=self.one.index)

            if self.mul:
                return F(one=two * self.one, mul=True, two=self.two)

            if self.div:
                return F(one=two * self.one, div=True, two=self.two)

            if self.add:
                if two < 0:
                    # if multiplying a negative number
                    return F(one=two * self.one, sub=True, two=-two * self.two)
                if two > 0:
                    # if multiplying a positive number
                    return F(one=two * self.one, add=True, two=two * self.two)

            if self.sub:
                if two < 0:
                    # if multiplying a negative number
                    return F(one=two * self.one, add=True, two=-two * self.two)
                if two > 0:
                    # if multiplying a positive number
                    return F(one=two * self.one, sub=True, two=two * self.two)

        if isinstance(other, list):
            # check 0th to see if tuple
            if isinstance(other[0], tuple):
                # if multiplying with a list of tuples
                # this is a theta
                raise NotImplementedError(
                    f'{self}*{other}: Multiplication with a parametric variable is not implemented yet.'
                )

            # make a parameter from the list
            two = make_P(other)
            # this by default is a parameter set

            if self.case == FCase.SUM:
                return F(
                    one=two,
                    mul=True,
                    two=self,
                    one_type=Elem.P,
                    two_type=Elem.F,
                )

            if self.mul:
                return F(one=two * self.one, mul=True, two=self.two)

            if self.div:
                return F(one=two * self.one, div=True, two=self.two)

            if self.add:
                return F(one=two * self.one, add=True, two=two * self.two)

            if self.sub:
                return F(one=two * self.one, sub=True, two=two * self.two)

        if isinstance(other, tuple):
            # if multiplying with a tuple
            # this is a theta
            raise NotImplementedError(
                f'{self}*{other}: Multiplication of function and parametric variable is not implemented yet.'
            )

        if isinstance(other, F):
            raise NotImplementedError(
                f'{self}*{other}: Multiplication of two functions is not implemented yet.'
            )

        if isinstance(other, V):
            raise NotImplementedError(
                f'{self}*{other}: Multiplication of variable and function is not implemented yet.'
            )

        if isinstance(other, T):
            raise NotImplementedError(
                f'{self}*{other}: Multiplication of function and parametric variable is not implemented yet.'
            )

        # what remains is P
        if self.case == FCase.SUM:
            return F(one=other, mul=True, two=self, one_type=Elem.P, two_type=Elem.F)

        if self.mul:
            return F(one=other * self.one, mul=True, two=self.two)

        if self.div:
            return F(one=other * self.one, div=True, two=self.two)

        if self.add:

            if other < 0:
                # multiplying a negative number
                return F(one=other * self.one, sub=True, two=-other * self.two)

            if other > 0:
                # multiplying a positive number
                return F(one=other * self.one, add=True, two=other * self.two)

        if self.sub:
            if other < 0:
                # multiplying a negative number
                return F(one=other * self.one, add=True, two=-other * self.two)
            if other > 0:
                # multiplying a positive number
                return F(one=other * self.one, sub=True, two=other * self.two)

    def __rmul__(
        self,
        other: (
            V
            | P
            | T
            | Self
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> Self:
        return self * other

    def __truediv__(
        self,
        other: (
            V
            | P
            | T
            | Self
            | int
            | float
            | tuple[int | float]
            | list[int | float | tuple[int | float]]
            | None
        ),
    ) -> Self:
        return self * (1 / other)

    # -----------------------------------------------------
    #                    Relational
    # -----------------------------------------------------
    def __eq__(self, other: Self | P | V | T):
        return C(self - other)

    def __le__(self, other: Self | P | V | T):

        return C(self - other, leq=True)

    def __ge__(self, other: Self | P | V | T):
        return C(-self + other, leq=True)

    def __lt__(self, other: Self | P | V | T):
        return self <= other

    def __gt__(self, other: Self | P | V | T):
        return self >= other

    # -----------------------------------------------------
    #                    Vector
    # -----------------------------------------------------

    def __call__(self, *key: list[I]) -> Self:

        if not key or (key == self.index):
            # if the index is an exact match
            # or no key is passed
            return self

        # if a subset is passed,
        # first create a product to match
        # the indices

        indices = list(product(*[list(product(*k)) for k in key]))

        # create a new function set to return
        f = F(**self.args)
        f.name, f.pname, f.n = self.name, self.pname, self.n
        f.A = []
        f.B = []
        f.P = []
        f.index = key

        # should be able to map these
        for n, index in enumerate(indices):
            # this helps weed out any None indices
            # i.e. skips
            if index is None:
                function = None
            else:
                # here the index could match the entire function index or
                # be the index of one or two

                # we can check whether it matches the entire function index first
                if index in self.map:
                    # if the index matches the entire function index
                    # then we can just use the function from the map
                    function = self.map[index]

                elif index[0] in self._one_map:
                    # if the index matches the first element of _one_map
                    # this is a one type function
                    index = list(self.map)[list(self._one_map).index(index[0])]

                elif index[0] in self._two_map:
                    # if the index matches the second element of _two_map
                    # this is a two type function
                    index = list(self.map)[list(self._two_map).index(index[0])]

                elif (
                    tuple(index[0] for _ in range(len(self.one.elements)))
                    in self._one_map
                ):
                    # if the index matches the first element of _one_map
                    index = list(self.map)[
                        list(self._one_map).index(
                            tuple(index[0] for _ in range(len(self.one.elements)))
                        )
                    ]

                elif (
                    tuple(index[0] for _ in range(len(self.two.elements)))
                    in self._two_map
                ):
                    # if the index matches the second element of _two_map
                    index = list(self.map)[
                        list(self._two_map).index(
                            tuple(index[0] for _ in range(len(self.two.elements)))
                        )
                    ]

                function: Self = self.map[index]
                f.map[index] = function
                f.one = function.one
                f.two = function.two
                f._one.append(self._one[n])
                f._two.append(self._two[n])
                # f.generate_matrices()

                var_index = self.index_flat[: len(self.variables)]
                mul_index = self.index_flat[
                    len(self.variables) : len(self.variables) + len(self.mul_parameters)
                ]
                rhs_index = self.index_flat[
                    len(self.variables)
                    + len(self.mul_parameters) : len(self.variables)
                    + len(self.mul_parameters)
                    + len(self.rhs_parameters)
                ]
                theta_index = self.index_flat[
                    len(self.variables)
                    + len(self.mul_parameters)
                    + len(self.rhs_parameters) :
                ]

                f.variables = [v(*i) for v, i in zip(self.variables, var_index)]
                f.mul_parameters = [
                    p(*i) for p, i in zip(self.mul_parameters, mul_index)
                ]
                f.rhs_parameters = [
                    r(*i) for r, i in zip(self.rhs_parameters, rhs_index)
                ]
                f.rhs_thetas = [t(*i) for t, i in zip(self.rhs_thetas, theta_index)]
                f.A.append(self.A[function.n])
                f.B.append(self.B[function.n])
                f.P.append(self.P[function.n])

            f._.append(function)

        return f

    def __getitem__(self, pos: int) -> F:
        return self._[pos]

    def __iter__(self) -> Self:
        return iter(self._)

    def __len__(self):
        return len(self._)

    # -----------------------------------------------------
    #                    Solution
    # -----------------------------------------------------

    def eval(self, n_sol: int = 0):
        """Evaluates the value of the function"""
        one, two = None, None
        # if this is a function, set
        # do evaluations for all the children and return
        if self.parent is None:
            return [f.eval(n_sol) for f in self._]

        def function_eval(function: Self):
            """Evaluates special cases of functions"""
            if function.case == FCase.SUM:
                # if this is a summation
                # avoid recursion
                return sum([v.X[n_sol] for v in function.variables])
            if function.case == FCase.NEGSUM:
                # if this is a negation
                # avoid recursion
                return -sum([v.X[n_sol] for v in function.variables])
            if function.case == FCase.NEGVAR:
                # if this is a negated variable
                # return the value of the variable
                return -function.two.X[n_sol]
            if function.case == FCase.FVAR:
                # if this is a variable being treated as a function
                # return the value of the variable
                return function.two.X[n_sol]

            return function.eval(n_sol)

        if self.parent.one_type == Elem.P:
            one = self.one
        elif self.parent.one_type == Elem.V:
            one = self.one.X[n_sol]
        elif self.parent.one_type == Elem.F:
            one = function_eval(self.one)

        if self.parent.two_type == Elem.P:
            two = self.two
        elif self.parent.two_type == Elem.V:
            two = self.two.X[n_sol]
        elif self.parent.two_type == Elem.F:
            two = function_eval(self.two)

        if self.mul:
            if not one:
                one = 1
            if not two:
                two = 1
            self.X[n_sol] = one * two
        if self.div:
            self.X[n_sol] = one / two
        if self.add:
            if not one:
                one = 0
            if not two:
                two = 0
            self.X[n_sol] = one + two
        if self.sub:
            if not one:
                one = 0
            if not two:
                two = 0
            self.X[n_sol] = one - two

        return self.X[n_sol]

    # -----------------------------------------------------
    #                    Hashing
    # -----------------------------------------------------

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)
