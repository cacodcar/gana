"""Program"""

import logging
import warnings
from dataclasses import dataclass, field
from typing import Literal

from gurobipy import Model as GPModel
from gurobipy import read as gpread
from IPython.display import Markdown, display
# from numpy import round as npround
# from numpy import abs as npabs
from numpy import array as nparray
from numpy import zeros as npzeros
from pandas import DataFrame
from ppopt.mp_solvers.solve_mpqp import mpqp_algorithm, solve_mpqp
from ppopt.mplp_program import MPLP_Program
from ppopt.plot import parametric_plot
from ppopt.solution import Solution as MPSolution

from ..operators.composition import inf, sup
from ..sets.cases import Elem, ICase, PCase
from ..sets.constraint import C
from ..sets.function import F as Func
from ..sets.index import I
from ..sets.objective import O
from ..sets.parameter import P
from ..sets.theta import T
from ..sets.variable import V
from .solution import Solution

logger = logging.getLogger("gana")
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


@dataclass
class Prg:
    """
    A mathematical program.

    Can be a linear (LP), integer (IP), or mixed-integer (MIP).

    :param name: Name of the program. Defaults to 'prog'.
    :type name: str, optional
    :param tol: Tolerance. Defaults to None.
    :type tol: float, optional
    :param canonical: Whether to use canonical form. Defaults to True.
    :type canonical: bool, optional
    :param tag: Tag for the program. Defaults to ''.
    :type tag: str, optional

    :ivar names: Names of declared sets
    :vartype names: list[str]
    :ivar sets: Object to hold set objects
    :vartype sets: Sets
    :ivar names_idx: Names of the index elements
    :vartype names_idx: list[str]
    :ivar indices: Index sets
    :vartype indices: list[X]
    :ivar variables: Variable sets
    :vartype variables: list[Var]
    :ivar thetas: Parametric variable sets
    :vartype thetas: list[PVar]
    :ivar functions: Function sets
    :vartype functions: list[Func]
    :ivar constraints: Constraint sets
    :vartype constraints: list[Cons]
    :ivar objectives: Objective sets
    :vartype objectives: list[Obj]

    :raises ValueError: If overwriting a set
    """

    name: str = field(default="prog")
    tol: float = field(default=None)
    canonical: bool = field(default=True)
    tag: str = field(default="")

    def __post_init__(self):

        # ---collections --------
        # index (I)
        self.index_sets: list[I] = []
        self.indices: list[I] = []

        # variable (V)
        self.variable_sets: list[V] = []
        self.variables: list[V] = []

        # parameter (P)
        self.parameter_sets: list[P] = []  # parameter sets
        # parameter set elements are just numeric

        # parametric variable (T)
        self.theta_sets: list[T] = []
        self.thetas: list[T] = []

        # function (F)
        self.function_sets: list[Func] = []
        self.functions: list[Func] = []

        # constraint (C)
        self.constraint_sets: list[C] = []
        self.constraints: list[C] = []

        self.categories_sets: dict[str, list[C]] = {}  # categories of constraint sets
        self.categories: dict[str, list[C]] = {}  # categories of constraints

        self.fcategories_sets: dict[str, list[Func]] = {}  # categories of function sets
        self.fcategories: dict[str, list[Func]] = {}  # categories of functions

        # objective (O)
        self.objectives: list[O] = []

        # ---names --------
        self.names: list[str] = []  # element names

        self.names_index_sets: list[str] = []  # index sets
        self.names_indices: list[str] = []  # elements
        self.names_variable_sets: list[str] = []  # variable sets
        self.names_parameter_sets: list[str] = []  # parameter sets
        self.names_theta_sets: list[str] = []  # parametric variable sets
        self.names_function_sets: list[str] = []  # function sets
        self.names_constraint_sets: list[str] = []  # constraints
        self.names_objectives: list[str] = []  # objectives

        # ---counts --------

        # index (I)
        self.n_index_sets: int = 0  # index sets
        self.n_index_elements: int = 0  # elements

        # variable (V)
        self.n_variable_sets: int = 0
        self.n_variables: int = 0

        # parameter (P)
        self.n_parameter_sets: int = 0

        # parametric variable (T)
        self.n_theta_sets: int = 0
        self.n_thetas: int = 0

        # function (F)
        self.n_function_sets: int = 0
        self.n_functions: int = 0

        # constraint (C)
        self.n_constraint_sets: int = 0
        self.n_constraints: int = 0

        # objective (O)
        self.n_objectives: int = 0  # objectives

        # flag for is optimized
        self.optimized = False

        # the solution object
        self.solution: dict[int, Solution | MPSolution] = {}

        # number of solutions
        self.n_sol: int = 0

        # solution matrix
        self.X: dict[int, list[float | int]] = {}

        # formulations available
        self.formulation: dict[int, GPModel | MPLP_Program] = {}

        # number of formulations
        self.n_for: int = 0

        # evaluations using parametric solutions
        self.evaluation: dict[int, dict[tuple[float, ...], list[float]]] = {}

        # number of evaluations by solution number
        self.n_eval: dict[int, int] = {}

        # solution types
        self.sol_types: dict[str, list[int]] = {"MIP": [], "mp": []}

    def add_index(self, name: str, index: I):
        """
        Adds new index to program

        :param name: name of index
        :type name: str
        :param index: index set to be added
        :type index: I
        """
        self.names.append(name)
        self.names_index_sets.append(name)
        # give the index a name
        index.name = name
        index._hash = hash(name)
        # This is the nth index set (0 indexed)
        index.n = self.n_index_sets
        # update the number of index sets
        self.n_index_sets += 1
        # update the list of indices
        self.index_sets.append(index)

    def add_indices(self, index: I, members: list[str] = None):
        """
        Adds indices from an index set to the program

        :param index: Index set who elements are to be added to the program.
        :type index: I
        :param members: List of members to be added to the index set.
        :type members: list[str], optional
        """

        if not members:
            # if specific members are not specified
            # add all of them as elements
            members = index.members

        # for unordered sets, the elements are set on the program
        for n, member in enumerate(members):

            if member not in self.names_indices:
                # if this element has not been added to the program before
                # create an element set
                element = I()
                # set the name
                element.name = member
                element._hash = hash(member)
                # this is the nth element (0 indexed)
                element.n = self.n_index_elements
                # update the number of elements
                self.n_index_elements += 1
                # this is a new element, so set the new name
                self.names_indices.append(member)
                self.indices.append(element)
                # if new element, it should be set on the program
                _new_elm = True

            else:

                # if the element is already set on the program
                # it can be part of another set already, get it from the program
                # e.g. human is both part of the kingdom index set animalia
                # and the family set hominidae
                # so its parent sets need to be animalia as well as hominidae
                # so update parent and add position in the new index set
                element: I = getattr(self, member)
                # these should not be set again
                _new_elm = False

            # update the index (I) as a parent
            element.parent.append(index)
            # update the position of the element in the index set
            element.pos.append(len(index._))
            # These are neither ordered or unordered sets
            element.ordered = None
            # element has only one member, itself
            element._ = [element]
            # now update the element in the index set
            index._.append(element)

            if _new_elm:
                # if this is a new element, set in
                setattr(self, member, element)

    def add_variable(self, name: str, variable: V):
        """
        Adds new variable set to program

        :param name: name of variable set
        :type name: str
        :param variable: variable set to be added
        :type variable: V
        """
        self.names.append(name)
        self.names_variable_sets.append(name)
        # give the variable a name
        variable.name = name
        # This is the nth variable set (0 indexed)
        variable.n = self.n_variable_sets
        # update the number of variable sets
        self.n_variable_sets += 1
        # update the list of variables
        self.variable_sets.append(variable)

        variable.birth_variables(n_start=self.n_variables)
        # update the list of variables
        self.variables.extend(variable._)
        self.n_variables += len(variable._)

    def mutate_variable(self, variable_ex: V, variable_new: V):
        """
        Mutates an existing variable set in the program

        :param variable_ex: existing variable set to be mutated
        :type variable_ex: V
        :param variable_new: incoming variable set to be added
        :type variable_new: V
        """
        # birth the new variables
        # inform that this is a mutation
        variable_new.birth_variables(mutating=True, n_start=self.n_variables)

        # the positions need to be pushed ahead
        pos_start = len(variable_ex)
        # note: if a variable already exists in the existing variable set
        # then, it is not added.
        # thus the position (and hence name) depends on the existing variables
        # this keeps a count of the number of variables added
        n = 0
        _name = variable_ex.name  # name of the existing variable set
        # iterate through all the new variables
        # update a list of new variable elements to be added
        var_add: list[V] = []
        for idx, v in variable_new.map.items():
            if idx is None:
                # for a None index, skip
                continue
            # only update exisitng variable
            # if not already in the existing variable set
            if idx not in variable_ex.map:
                # set the position of the new variable
                _pos = pos_start + n
                v.pos = _pos
                # set the name based on position in existing variable set
                v.name = f"{_name}[{_pos}]"  # give a name
                # set the parent to the existing variable set
                v.parent = variable_ex
                # update the variable map
                variable_ex.map[idx] = v
                # update the variable set
                variable_ex._.append(v)
                # and the added variables
                var_add.append(v)
                # update the iter counter
                n += 1
        if n > 0:
            variable_ex.n_splices += 1
            # update the existing variable index
            # only if something new has been added
            var_ex_idx = tuple(
                [i[0] if isinstance(i, list) else i for i in variable_ex.index]
            )
            var_new_idx = tuple(
                [i[0] if isinstance(i, list) else i for i in variable_new.index]
            )

            if variable_ex.n_splices > 2:
                # if there are more than 2 splices
                variable_ex.index = {*variable_ex.index, var_new_idx}
            else:
                variable_ex.index = {var_ex_idx, var_new_idx}
            self.n_variables += n
            self.variables.extend(var_add)

    def add_parameter(self, name: str, parameter: P):
        """
        Adds new parameter set to program

        :param name: name of parameter set
        :type name: str
        :param parameter: parameter set to be added
        :type parameter: P
        """
        self.names.append(name)
        self.names_parameter_sets.append(name)
        # give the parameter a name
        if not parameter.name:
            parameter.name = name
        # This is the nth parameter set (0 indexed)
        parameter.n = self.n_variable_sets
        # update the number of parameter sets
        self.n_parameter_sets += 1
        # update the list of parameters
        self.parameter_sets.append(parameter)

    def mutate_parameter(self, parameter_ex: P, parameter_new: P):
        """
        Mutates an existing parameter set in the program

        :param parameter_ex: existing parameter set to be mutated
        :type parameter_ex: P
        :param parameter_new: incoming parameter set to be added
        :type parameter_new: P
        """
        n = 0  # count of parameters added to set
        for idx, p in parameter_new.map.items():

            if idx is None:
                # for a None index, skip
                continue

            if idx in parameter_ex.map:
                # warn if number is being replaced
                warnings.warn(
                    f"The value{parameter_ex.map[idx]} is being overwritten by {p} at index {idx}"
                )

            # set the position of the new parameter
            parameter_ex.map[idx] = p
            parameter_ex._.append(p)
            n += 1

        if n > 0:
            parameter_ex.n_splices += 1
            # update the existing parameter index
            # only if something new has been added
            if parameter_ex.n_splices > 2:
                parameter_ex.index = {*parameter_ex.index, parameter_new.index}
            else:
                parameter_ex.index = {parameter_ex.index, parameter_new.index}

    def add_theta(self, name: str, theta: T):
        """
        Adds new theta set to program

        :param name: name of theta set
        :type name: str
        :param theta: theta set to be added
        :type theta: T
        """
        self.names.append(name)
        self.names_theta_sets.append(name)
        # give the theta a name
        theta.name = name
        # This is the nth theta set (0 indexed)
        theta.n = self.n_theta_sets
        # update the number of theta sets
        self.n_theta_sets += 1
        # update the list of thetas
        self.theta_sets.append(theta)

        theta.birth_thetas(n_start=self.n_thetas)
        # update the list of thetas
        self.thetas.extend(theta._)
        self.n_thetas += len(theta._)

    def update_theta(self, constraint: C):
        """
        Updates the theta set and thetas in a constraint

        :param constraint: constraint with thetas to be updated
        :type constraint: C
        """
        for n, theta in enumerate(constraint.function.rhs_thetas):
            if theta.parent is None:
                self.add_theta(name=f"θ{self.n_theta_sets}", theta=theta)
                # the last theta added is the one just made
                theta = self.theta_sets[-1]
                # replace the theta in the constraint rhs list
                constraint.function.rhs_thetas[n] = theta
                # Create the F and Z matrices for the constraint
                # this only handles addition or subtraction with T

            if (
                constraint.function.one_type == Elem.F
                and constraint.function.one.two_type == Elem.T
            ):
                # this is of the form V/F +- Th1 +- Th2
                if constraint.function.add:
                    constraint.function.F = [
                        i + [-1] for i in constraint.function.one.F
                    ]
                    constraint.function.Z = [
                        i + [theta._[pos].n]
                        for pos, i in enumerate(constraint.function.one.Z)
                    ]
                if constraint.function.sub:
                    constraint.function.F = [i + [1] for i in constraint.function.one.F]
                    constraint.function.Z = [
                        i + [theta.n] for i in constraint.function.one.Z
                    ]
                    constraint.function.Z = [
                        i + [theta._[pos].n]
                        for pos, i in enumerate(constraint.function.one.Z)
                    ]
            else:

                # this is of the form V/F +- Th1
                if constraint.function.add:
                    constraint.function.F = [[-1]] * len(constraint.one)
                    constraint.function.Z = [
                        [theta._[pos].n] for pos in range(len(constraint.one))
                    ]
                if constraint.function.sub:
                    constraint.function.F = [[1]] * len(constraint.one)
                    constraint.function.Z = [
                        [theta._[pos].n] for pos in range(len(constraint.one))
                    ]

            for n, cons in enumerate(constraint._):
                # update the constraint element matrices
                cons.function.F = constraint.function.F[n]
                cons.function.Z = constraint.function.Z[n]
                # update two
                cons.function.two = theta[n]
                cons.function.give_name()

    def mutate_theta(self, theta_ex: T, theta_new: T):
        """
        Mutates an existing theta set in the program

        :param theta_ex: existing theta set to be mutated
        :type theta_ex: T
        :param theta_new: incoming theta set to be added
        :type theta_new: T
        """

        # birth the new thetas
        # inform that this is a mutation
        theta_new.birth_thetas(mutating=True, n_start=self.n_thetas)

        # the positions need to be pushed ahead
        pos_start = len(theta_ex)
        # note: if a theta already exists in the existing theta set
        # then, it is not added.
        # thus the position (and hence name) depends on the existing thetas
        # this keeps a count of the number of thetas added
        n = 0
        _name = theta_ex.name  # name of the existing theta set
        # iterate through all the new thetas
        # update a list of new theta elements to be added
        tht_add: list[T] = []
        for idx, t in theta_new.map.items():
            if idx is None:
                # for a None index, skip
                continue
            # only update exisitng theta
            # if not already in the existing theta set
            if idx not in theta_ex.map:
                # set the position of the new theta
                _pos = pos_start + n
                t.pos = _pos
                # set the name based on position in existing theta set
                t.name = f"{_name}[{_pos}]"  # give a name
                # set the parent to the existing theta set
                t.parent = theta_ex
                # update the theta map
                theta_ex.map[idx] = t
                # update the theta set
                theta_ex._.append(t)
                # and the added thetas
                tht_add.append(t)
                # update the iter counter
                n += 1
        if n > 0:
            # update the existing theta index
            # only if something new has been added
            tht_ex_idx = tuple(
                [i[0] if isinstance(i, list) else i for i in theta_ex.index]
            )
            tht_new_idx = tuple(
                [i[0] if isinstance(i, list) else i for i in theta_new.index]
            )
            theta_ex.index = {tht_ex_idx, tht_new_idx}
            self.n_thetas += n
            self.thetas.extend(tht_add)

    def add_function(self, name: str, function: Func):
        """
        Add a function set to the program

        :param name: name of function
        :type name: str
        :param function: function object
        :type function: F
        """
        self.names.append(name)
        self.names_function_sets.append(name)
        # give the function a name
        # but do not add it to name
        # we want the hash to the equation
        # but the attribute name to be name
        function.pname = name
        # This is the nth function set (0 indexed)
        function.n = self.n_function_sets
        # update the number of function sets
        self.n_function_sets += 1
        # update the list of functions
        self.function_sets.append(function)

        # # update the list of functions
        self.functions.extend(function._)
        for n, f in enumerate(function._):
            # this is the nth function declared
            f.n = self.n_functions + n

        # # update the number of functions
        self.n_functions += len(function._)

    def replace_function(self, function_ex: Func, function_new: Func):
        """
        Replaces an existing function set in the program

        :param function_ex: existing function set to be mutated
        :type function_ex: F
        :param function_new: new function set to replace the existing one
        :type function_new: F
        """

        # just replace the existing function set
        # take the old constraints number and pname
        function_new.n = function_ex.n

        function_new.pname = function_ex.pname
        # replace the function set in the program
        self.function_sets[self.function_sets.index(function_ex)] = function_new
        # update the list of functions

        # first, number the functions in the new set
        for n, f in enumerate(function_new._):
            f.n = self.n_functions + n

        # second, remove the old functions
        self.functions = (
            self.functions[: function_ex._[0].n]
            + self.functions[function_ex._[-1].n + 1 :]
        )

        # third, add the new functions
        self.functions.extend(function_new._)

        # four, clean up the features_in list for variables in old function
        for v in function_ex.variables:
            if function_ex in v.min_by:
                v.min_by.remove(function_ex)

            for var in v._:
                for func in function_ex._:
                    if func in var.min_by:
                        _min_by = var.min_by
                        _min_by.remove(func)
                        var.min_by = _min_by

    def add_constraint(self, name: str, constraint: C):
        """
        Adds a constraint set to the program

        :param name: name of constraint
        :type name: str
        :param constraint: constraint object
        :type constraint: C
        """
        self.names.append(name)
        self.names_constraint_sets.append(name)
        # give the constraint a name
        # but do not add it to name
        # we want the hash to the equation
        # but the attribute name to be name
        constraint.pname = name
        # This is the nth constraint set (0 indexed)
        constraint.n = self.n_constraint_sets
        # update the number of constraint sets
        self.n_constraint_sets += 1
        # update the list of constraints
        self.constraint_sets.append(constraint)

        constraint.update_variables()

        # update the list of constraints
        self.constraints.extend(constraint._)
        for n, c in enumerate(constraint._):
            # this is the nth constraint declared
            c.n = self.n_constraints + n

        # update the number of constraints
        self.n_constraints += len(constraint._)

        if constraint.function.rhs_thetas:
            # if the constraint has thetas in them
            # then update the thetas in the function
            self.update_theta(constraint)

    def replace_constraint(self, constraint_ex: C, constraint_new: C):
        """
        Replaces an existing constraint set in the program

        :param constraint_ex: existing constraint set to be mutated
        :type constraint_ex: C
        :param constraint_new: new constraint set to replace the existing one
        :type constraint_new: C
        """
        # just replace the existing constraint set
        # take the old constraints number and pname
        constraint_new.n = constraint_ex.n
        constraint_new.pname = constraint_ex.pname
        if not constraint_ex.category == "General":

            constraint_new.categorize(constraint_ex.category)

        # replace the constraint set in the program
        # self.constraint_sets[self.constraint_sets.index(constraint_ex)] = constraint_new
        self.constraint_sets[constraint_ex.n] = constraint_new

        # replace the constraint in the program
        # let new constraint take n of the old constraint
        for cons_new, cons_ex in zip(constraint_new._, constraint_ex._):

            # self.constraints[self.constraints.index(cons_ex)] = cons_new
            self.constraints[cons_ex.n] = cons_new

            cons_new.n = cons_ex.n

        for cons_ex, cons_new in zip(constraint_ex._, constraint_new._):
            cons_new.cons_by_pos = cons_ex.cons_by_pos
            for v in cons_ex.variables:
                v.cons_by[cons_ex.cons_by_pos[v]] = cons_new

            for v in cons_new.variables:
                if cons_new not in v.cons_by:
                    cons_new.cons_by_pos[v] = len(v.cons_by)
                    v.cons_by.append(cons_new)

    def add_objective(self, objective: O):
        """
        Adds an objective set to the program

        :param objective: objective object
        :type objective: O
        """
        self.names.append(objective.pname)
        self.names_objectives.append(objective.pname)
        # This is the nth objective set (0 indexed)
        objective.n = self.n_objectives
        # update the number of objective sets
        self.n_objectives += 1
        # update the list of objectives
        self.objectives.append(objective)
        self.function_sets.append(objective.function)
        objective.update_variables()

    def __setattr__(self, name, value) -> None:

        _mutation = False  # skip setting set

        if isinstance(value, I):

            if name not in self.names_index_sets and name not in self.names_indices:

                if len(value.members) == 1 and value.members[0] == name:
                    # There is a special case, where a self contained set is passed
                    # in that case, add the index
                    self.add_index(name, value)
                    # but the only set it contains is itself
                    value._ = [value]
                    value.case = ICase.SELF

                else:

                    # check if index already exists in the program
                    # or is the name of an element
                    # element are set by their parents
                    # if this is a new object, it can be safely added
                    self.add_index(name, value)

                    if value.ordered:
                        # for ordered set, the elements are not set on the program
                        value.birth_elements()

                    else:
                        self.add_indices(value)

            elif name not in self.names_indices:
                # the set could be already declared, and mutable
                # is being declared as part of another index set
                # in which case get the original set to update
                index_ex: I = getattr(self, name)  # existing index set

                # if not mutable, raise error
                if not index_ex.mutable:
                    raise ValueError(
                        f"{self.name}: Overwriting index {name}. Set mutable=True if index needs to be updated"
                    )

                # if an index is being mutated, skip setting
                _mutation = True

                # # for collections, each element is a set of size 1
                if not value.ordered:
                    # update the exisiting index set with the new elements
                    _members = []
                    for member in value.members:
                        if member not in index_ex.members:
                            # if the member is not already in the index set
                            _members.append(member)

                    self.add_indices(index_ex, _members)

        elif isinstance(value, V):

            if name not in self.names_variable_sets:
                if value.name not in self.names_variable_sets:
                    # if variable set is new, add it to the program
                    # another check we do, is if variable is being added to the program
                    # but the variable already exists
                    # this happens in a case such as this:
                    # p.f0 = p.v - 3
                    # p.f1 = p.f0 + 3
                    # This is returning a variable set that already exists in the program
                    if not any(None for _ in value.index):
                        self.add_variable(name, value)

            else:
                variable_ex: V = getattr(self, name)  # existing variable set

                # if not mutable, raise error
                if not variable_ex.mutable:
                    raise ValueError(
                        f"{self.name}: Overwriting variable {name}. Set mutable=True if variable needs to be updated"
                    )

                # if an index is being mutated, skip setting
                _mutation = True

                # give a name because
                # the incoming variable set will birth variables too
                # and they will need a name
                value.name = name
                self.mutate_variable(variable_ex, value)

        elif isinstance(value, P):
            if name not in self.names_parameter_sets:
                # if parameter is new, add it to the program

                if value.case in [PCase.NEGSET, PCase.SET]:
                    self.add_parameter(name, value)

            else:
                parameter_ex: P = getattr(self, name)  # existing parameter set

                # if not mutable, raise error
                if not parameter_ex.mutable:
                    raise ValueError(
                        f"{self.name}: Overwriting parameter {name}. Set mutable=True if parameter needs to be updated"
                    )

                # if an index is being mutated, skip setting
                _mutation = True
                # mutate the parameter
                self.mutate_parameter(parameter_ex, value)

        elif isinstance(value, T):

            if name not in self.names_theta_sets:
                self.add_theta(name, value)

            else:
                theta_ex: T = getattr(self, name)
                if not theta_ex.mutable:
                    raise ValueError(
                        f"{self.name}: Overwriting theta {name}. Set mutable=True if theta needs to be updated"
                    )
                _mutation = True
                self.mutate_theta(theta_ex, value)

        elif isinstance(value, Func):
            if name not in self.names_function_sets:
                self.add_function(name, value)
            else:
                # if function is being mutated
                # replace existing function with the new one
                self.replace_function(getattr(self, name), value)
                # but still set it

        elif isinstance(value, C):

            if name not in self.names_constraint_sets:
                self.add_constraint(name, value)

            else:
                self.replace_constraint(getattr(self, name), value)

        elif isinstance(value, O):
            self.add_objective(value)

        if not _mutation:
            super().__setattr__(name, value)

    # --------------------------------------------------
    #               Subsets
    # --------------------------------------------------

    @property
    def nncons_sets(self) -> list[C]:
        """non-negativity constraint sets"""
        return [x for x in self.constraint_sets if x.nn]

    @property
    def eqcons_sets(self) -> list[C]:
        """equality constraint sets"""
        return [x for x in self.constraint_sets if not x.leq]

    @property
    def leqcons_sets(self) -> list[C]:
        """less than or equal constraint sets"""
        return [x for x in self.constraint_sets if x.leq and not x.nn]

    def nncons(self, n: bool = False) -> list[int | C]:
        """non-negativity constraints"""
        if n:
            return [x.n for x in self.constraints if x.nn]
        return [x for x in self.constraints if x.nn]

    def eqcons(self, n: bool = False) -> list[int | C]:
        """equality constraints"""
        if n:
            return [x.n for x in self.constraints if not x.leq]
        return [x for x in self.constraints if not x.leq]

    def leqcons(self, n: bool = False) -> list[int | C]:
        """less than or equal constraints"""
        if n:
            return [x.n for x in self.constraints if x.leq and not x.nn]
        return [x for x in self.constraints if x.leq and not x.nn]

    def cons(self, n: bool = False) -> list[int | C]:
        """constraints"""
        return self.leqcons(n) + self.eqcons(n) + self.nncons(n)

    def nnvars(self, n: bool = False) -> list[int | V]:
        """non-negative variables"""
        if n:
            return [x.n for x in self.variables if x.nn]
        return [x for x in self.variables if x.nn]

    def bnrvars(self, n: bool = False) -> list[int | V]:
        """binary variables"""
        if n:
            return [x.n for x in self.variables if x.bnr]
        return [x for x in self.variables if x.bnr]

    def itgvars(self, n: bool = False) -> list[int | V]:
        """integer variables"""
        if n:
            return [x.n for x in self.variables if x.itg]
        return [x for x in self.variables if x.itg]

    def nonbnritgvars(self, n: bool = False) -> list[int | V]:
        """non-binary and integer variables"""
        if n:
            return [x.n for x in self.variables if x.itg and not x.bnr]
        return [x for x in self.variables if x.itg and not x.bnr]

    def cntbnrvars(self, n: bool = False) -> list[int | V]:
        """continuous and binary variables
        integer variables are excluded
        """
        if n:
            return [x.n for x in self.variables if not x.itg or x.bnr]
        return [x for x in self.variables if not x.itg or x.bnr]

    def cntvars(self, n: bool = False) -> list[int | V]:
        """continuous variables"""
        if n:
            return [x.n for x in self.variables if not x.bnr and not x.itg]
        return [x for x in self.variables if not x.bnr and not x.itg]

    def renumber(self):
        """Renumbers the constraints, just to be sure"""
        for n, c in enumerate(self.cons()):
            c.n = n

    # --------------------------------------------------
    #               Matrices
    # --------------------------------------------------

    # DONOT call these for large programs
    # Going to run into memory issues
    # TODO: make sparse matrix options

    @property
    def B(self) -> list[float]:
        """RHS Parameter vector"""
        return [c.B for c in self.cons()]

    @property
    def A(self) -> list[list[float]]:
        """Matrix of Variable coefficients"""
        constraints = self.cons()
        _A = []
        for _ in constraints:
            row = [0] * len(self.variables)
            _A.append(row)

        for n, c in enumerate(constraints):
            for x, a in zip(c.P, c.A):
                _A[n][x] = a
        return _A

    @property
    def F(self) -> list[list[float]]:
        """Matrix of Parameteric Variable coefficients"""
        constraints = self.cons()
        _F = []
        for _ in constraints:
            row = [0] * len(self.thetas)
            _F.append(row)

        for n, c in enumerate(constraints):
            for z, f in zip(c.Z, c.F):
                _F[n][z] = f
        return _F

    @property
    def C(self) -> list[float]:
        """Objective Coefficients"""
        # no objectives have been set
        if len(self.objectives) == 0:
            return []

        if len(self.objectives) == 1:
            # only one objective has been set
            obj = self.objectives[0]

            _C = [0] * len(self.variables)  # initialize with zeros
            for n, v in enumerate(obj.variables):
                _C[obj.P[n]] = obj.C[n]

        return _C

    @property
    def P(self) -> list[list[int]]:
        """Structure of the constraint matrix"""
        return [c.P for c in self.cons()]

    @property
    def Z(self) -> list[list[int]]:
        """Structure of the constraint matrix"""
        return [c.Z for c in self.cons()]

    @property
    def G(self) -> list[list[float]]:
        """Matrix of Variable coefficients for type:

        g < = 0
        """
        _G = [[0] * len(self.variables) for _ in range(len(self.leqcons()))]

        for n, c in enumerate(self.leqcons()):
            for x, a in zip(c.P, c.A):
                if x is not None:
                    _G[n][x] = a

        return _G

    @property
    def H(self) -> list[list[float]]:
        """
        Matrix of Variable coefficients for type:

        h = 0
        """
        _H = [[0] * len(self.variables) for _ in range(len(self.eqcons()))]
        for n, c in enumerate(self.eqcons()):
            for x, a in zip(c.P, c.A):
                if x is not None:
                    _H[n][x] = a
        return _H

    @property
    def NN(self) -> list[list[float]]:
        """Matrix of Variable coefficients for non negative cons"""
        _NN = [[0] * len(self.variables) for _ in range(len(self.variables))]

        for n, v in enumerate(self.variables):
            if v in self.nnvars():
                _NN[n][n] = -1
        return _NN

    @property
    def A_with_NN(self) -> list[list[float]]:
        """Matrix of Variable coefficients with non-negative constraints"""
        return self.A + self.NN

    @property
    def B_with_NN(self) -> list[float]:
        """RHS Parameter vector with non-negative constraints"""
        return self.B + [0] * len(self.nnvars())

    @property
    def CrA(self) -> list[list[float]]:
        """Critical Region A matrix"""
        CrA_UB = [[0] * len(self.thetas) for _ in range(len(self.thetas))]
        CrA_LB = [[0] * len(self.thetas) for _ in range(len(self.thetas))]

        for n in range(len(self.thetas)):
            CrA_UB[n][n] = 1.0
            CrA_LB[n][n] = -1.0

        CrA_ = []

        for n in range(len(self.thetas)):
            CrA_.append(CrA_UB[n])
            CrA_.append(CrA_LB[n])

        return CrA_

    @property
    def CrB(self) -> list[float]:
        """Critical Region RHS vector"""
        CrB_ = []
        for t in self.thetas:
            CrB_.append(t.ub)
            CrB_.append(-t.lb)

        return CrB_

    def make_A_df(self, longname: bool = False) -> DataFrame:
        """
        Create a DataFrame from the A matrix.

        :param longname: Whether to use long names for variables. Defaults to False.
        :type longname: bool

        :return: Columns are the variables, rows are the constraints.
        :rtype: DataFrame
        """
        if longname:
            return DataFrame(
                self.A,
                columns=[v.longname for v in self.variables],
                index=[c.longname for c in self.cons()],
            )
        return DataFrame(
            self.A,
            columns=[v.name for v in self.variables],
            index=[c.name for c in self.cons()],
        )

    def make_B_df(self, longname: bool = False) -> DataFrame:
        """
        Create a DataFrame from the B vector.

        :param longname: Whether to use long names for variables. Defaults to False.
        :type longname: bool

        :return: Single column DataFrame with the RHS values.
        :rtype: DataFrame
        """

        if longname:
            index = [c.longname for c in self.cons()]
        else:
            index = [c.name for c in self.cons()]

        return DataFrame(self.B, columns=["RHS"], index=index)

    def make_C_df(self, longname: bool = False) -> DataFrame:
        """
        Create a DataFrame from the C matrix.

        :param longname: Whether to use long names for variables. Defaults to False.
        :type longname: bool

        :return: Single row DataFrame with the objective coefficients.
        :rtype: DataFrame
        """

        if longname:
            columns = [v.longname for v in self.variables]
        else:
            columns = [v.name for v in self.variables]
        return DataFrame([self.C], columns=columns, index=["Minimize"])

    def make_df(self, longname: bool = False) -> DataFrame:
        """
        Create a DataFrame from the model.

        :param longname: Whether to use long names for variables. Defaults to False.
        :type longname: bool

        :return: A DataFrame with the A matrix, B vector, and C vector.
        :rtype: DataFrame
        """

        if longname:
            index = ["Minimize"] + [c.longname for c in self.cons()]
            columns = [v.longname for v in self.variables] + ["RHS"]
            index = ["Minimize"] + [c.longname for c in self.cons()]
            columns = [v.longname for v in self.variables] + ["RHS"]
        else:
            index = ["Minimize"] + [c.name for c in self.cons()]
            columns = [v.name for v in self.variables] + ["RHS"]
            index = ["Minimize"] + [c.name for c in self.cons()]
            columns = [v.name for v in self.variables] + ["RHS"]
        data = []
        for n, d in enumerate(self.A):
            d.append(self.B[n])
            data.append(d)

        data = [self.C + [0]] + data

        return DataFrame(data, columns=columns, index=index)

    def make_CrA_df(self, longname: bool = False) -> DataFrame:
        """Creates a DataFrame from the Critical Region A matrix."""

        if longname:
            columns = [t.longname for t in self.thetas]
            index = sum([[t.longname] * 2 for t in self.thetas], [])
        else:
            columns = [t.name for t in self.thetas]
            index = sum([[t.name] * 2 for t in self.thetas], [])

        return DataFrame(self.CrA, columns=columns, index=index)

    def make_CrB_df(self, longname: bool = False) -> DataFrame:
        """Creates a DataFrame from the Critical Region RHS vector."""

        if longname:
            index = sum([[t.longname] * 2 for t in self.thetas], [])
        else:
            index = sum([[t.name] * 2 for t in self.thetas], [])

        return DataFrame(self.CrB, columns=["RHS"], index=index)

    def make_F_df(self, longname: bool = False) -> DataFrame:
        """Creates a DataFrame from the Theta coefficients matrix."""
        if longname:
            columns = [t.longname for t in self.thetas]
            index = [c.longname for c in self.cons()]
        else:
            columns = [t.name for t in self.thetas]
            index = [c.name for c in self.cons()]

        return DataFrame(self.F, columns=columns, index=index)

    # --------------------------------------------------
    #               Write
    # --------------------------------------------------

    def mps(self, name: str = None):
        """MPS File"""

        logger.info(f"Generating {name or self.name}.mps")

        # 1 unit of whitespace
        ws = " "
        # renumber the constraints based on order in .cons()
        # as opposed to order of declaration
        self.renumber()

        leqcons = self.leqcons()
        eqcons = self.eqcons()
        cntvars = self.cntvars()
        nnvars = self.nnvars()
        bnrvars = self.bnrvars()
        cntbnrvars = self.cntbnrvars()
        nonbnritgvars = self.nonbnritgvars()

        # _C = self.C
        # _A = self.A

        # write the MPS file
        with open(f"{name or self.name}.mps", "w", encoding="utf-8") as f:

            # header: NAME          MODEL_NAME
            f.write(f"NAME{ws*10}{self.name.upper()}\n")

            # Here the constraint types are defined
            f.write("ROWS\n")

            if self.objectives:
                # the objective is: N   OBJECTIVE_NAME
                f.write(f"{ws}N{ws*3}{self.objectives[-1].mps()}\n")

            for c in leqcons:
                # less than or equal constraints are: L   CONSTRAINT_NAME
                f.write(f"{ws}L{ws*3}{c.mps()}\n")

            for c in eqcons:
                # equality constraints are: E   CONSTRAINT_NAME
                f.write(f"{ws}E{ws*3}{c.mps()}\n")

            # Here the variables are defined along with their coefficients
            # in each of the constraints that they feature in

            f.write("COLUMNS\n")
            for v in cntbnrvars:
                # For each variable, we write:
                # V_NAME    CONSTRAINT_NAME    COEFFICIENT
                # for all variables, these are ordered
                # as they are added based on declaration
                vs = len(v.mps())
                # for constraints/functions/objectives that they feature in
                for c in v.cons_by:
                    # this captures the length of the variable name
                    # variable names are just Vn where n is order of precedence
                    vfs = len(c.mps())
                    f.write(ws * 4)
                    f.write(v.mps())
                    f.write(ws * (10 - vs))
                    f.write(c.mps())
                    f.write(ws * (10 - vfs))
                    # C variable coefficients are a vector
                    f.write(f"{c.matrix[v.n]}")
                    f.write("\n")

                for o in v.min_by:
                    # this captures the length of the variable name
                    # variable names are just Vn where n is order of precedence
                    vfs = len(o.mps())
                    f.write(ws * 4)
                    f.write(v.mps())
                    f.write(ws * (10 - vs))
                    f.write(o.mps())
                    f.write(ws * (10 - vfs))
                    f.write(f"{o.function[0].matrix[v.n]}")
                    f.write("\n")

            if nonbnritgvars:
                f.write(f"{ws*4}MARK0000{ws*2}'MARKER'{ws*17}'INTORG'\n")
                for v in nonbnritgvars:
                    vs = len(v.mps())
                    # for constraints/functions/objectives that they feature in
                    for c in v.cons_by:
                        # this captures the length of the variable name
                        # variable names are just Vn where n is order of precedence
                        vfs = len(c.mps())
                        f.write(ws * 4)
                        f.write(v.mps())
                        f.write(ws * (10 - vs))
                        f.write(c.mps())
                        f.write(ws * (10 - vfs))
                        # C variable coefficients are a vector
                        f.write(f"{c.matrix[v.n]}")
                        f.write("\n")

                    for o in v.min_by:
                        # this captures the length of the variable name
                        # variable names are just Vn where n is order of precedence
                        vfs = len(o.mps())
                        f.write(ws * 4)
                        f.write(v.mps())
                        f.write(ws * (10 - vs))
                        f.write(o.mps())
                        f.write(ws * (10 - vfs))

                        f.write(f"{o.function[0].matrix[v.n]}")
                        f.write("\n")

                f.write(f"{ws*4}MARK0000{ws*2}'MARKER'{ws*17}'INTEND'\n")

            # This gives the right-hand side of the constraints
            f.write("RHS\n")
            for n, c in enumerate(leqcons + eqcons):
                # For each constraint, we write:
                # RHSn    CONSTRAINT_NAME    RHS_VALUE
                f.write(ws * 4)
                f.write(f"RHS{n}")
                f.write(ws * (10 - len(f"RHS{n+1}")))
                f.write(c.mps())
                f.write(ws * (10 - len(c.mps())))
                f.write(f"{c.B}")
                f.write("\n")

            f.write("BOUNDS\n")
            # for continuous variables that are nonnegative, we write:
            # LO BND1    VARIABLE_NAME    0
            for v in nnvars:
                if v in cntvars:
                    f.write(f"{ws}LO{ws}BND1{ws*4}{v.mps()}{ws*8}{0}\n")

            # for integer variables that are binary, we write:
            # BV BND1    VARIABLE_NAME
            for v in bnrvars:
                f.write(f"{ws}BV{ws}BND1{ws*5}{v.mps()}\n")

            for v in nonbnritgvars:
                vs = len(v.mps())
                if v.nn:
                    f.write(f"{ws}LI{ws}BOUND{ws*4}{v.mps()}{ws*(10 - vs)}{0}\n")
                else:
                    logger.warning(
                        "!!! Some solvers need bounds for integer variables provided explicitly"
                    )
                    logger.warning(
                        f"!!! This can cause issues when providing unbounded integer variables such as {v}"
                    )

            # CLOSE the MPS file
            f.write("ENDATA")

    def lp(self):
        """LP File"""
        m = self.gurobi()
        m.write(f"{self.name}.lp")

    # --------------------------------------------------
    #               Optimize
    # --------------------------------------------------
    def opt(self, using: str = "gurobi"):
        """Determine the optimal solution to the program"""

        if using == "gurobi":
            m = self.gurobi()

            self.formulation[self.n_for] = m
            self.n_for += 1

            logger.info(f"Optimizing {self} using {using}")
            m.optimize()
            try:
                logger.info("Solution found. Use .sol() to display it")

                self.X[self.n_sol] = [v.X for v in m.getVars()]

                _variables = [v for v in self.variables if v.cons_by]
                for v, val in zip(_variables, self.X[self.n_sol]):

                    v.X[self.n_sol] = val

                for c in self.constraint_sets:
                    c.function.solution(n_sol=self.n_sol)

                self.objectives[-1].X = m.ObjVal
                self.optimized = True

                logger.info("Creating Solution object, check.solution")

                self.solution[self.n_sol] = self.birth_solution()
                self.sol_types["MIP"].append(self.n_sol)
                self.n_sol += 1
            except AttributeError:
                logger.warning("!!! No solution found. Check the model.")

    def solve(
        self,
        using: Literal[
            "combinatorial",
            "combinatorial_parallel",
            "combinatorial_parallel_exp",
            "graph",
            "graph_exp",
            "graph_parallel",
            "graph_parallel_exp",
            "combinatorial_graph",
            "geometric",
            "geometric_parallel",
            "geometric_parallel_exp",
        ] = "combinatorial",
        tol_mat: float = 1e-9,
        round_off: int = 4,
    ):
        """Solve the multiparametric program"""

        m = self.ppopt()
        self.formulation[self.n_for] = m
        self.n_for += 1
        logger.info(f"Solving {self} using PPOPT {using} algorithm")

        sol = solve_mpqp(m, getattr(mpqp_algorithm, using))
        if sol.critical_regions:

            # TODO: do not delete
            # this creates actual programs for each critical region
            # _p = Prg(f"{self}_var_eval")
            # _p.i = I(size=self.n_thetas)
            # _p.t = V(_p.i)

            # for n, cr in enumerate(sol.critical_regions):
            #     for mat in ["A", "d", "E"]:
            #         # clean up small values
            #         # set below tolerance to zero
            #         # round off to specified decimal places
            #         getattr(cr, mat)[npabs(getattr(cr, mat)) < tol_mat] = 0
            #         setattr(cr, mat, npround(getattr(cr, mat), decimals=round_off))
            #     A = cr.A.T
            #     # write the evaluation function
            #     f = sum(list(a) * t for a, t in zip(A, _p.t._)) + list(cr.b)

            #     setattr(_p, f"v_cr{n}", f)
            #     # this add the equations determining variable values
            #     # as a function of parametric variables
            #     # in a dictionary for each variable to hold them
            #     for _v, _f in zip(self.variables, f):
            #         _v.eval_funcs.setdefault(self.n_sol, {})[n] = _f

            self.solution[self.n_sol] = sol
            self.sol_types["mp"].append(self.n_sol)
            self.n_sol += 1

    def eval(
        self, *theta_vals: float, n_sol: int = 0, roundoff: int = 4
    ) -> list[float]:
        """
        Evaluates the variable value as a function of parametric variables

        :param theta_vals: values of the parametric variables
        :type theta_vals: float
        :param n_sol: solution number, defaults to 0
        :type n_sol: int, optional
        :param roundoff: round off the evaluated value, defaults to 4
        :type roundoff: int, optional

        :returns: list of values
        :rtype: list[float]

        :raises ValueError: if number of theta values provided does not match number of thetas in the problem
        """
        if len(theta_vals) != self.n_thetas:
            raise ValueError(
                f"Problem has {self.n_thetas} thetas, provided {len(theta_vals)} values",
            )

        _theta_vals = nparray([[v] for v in theta_vals])
        sol = self.solution[n_sol].evaluate(_theta_vals)
        sol = [round(float(val[0]), roundoff) for val in sol]

        self.evaluation.setdefault(n_sol, {})
        self.n_eval.setdefault(n_sol, 0)

        self.evaluation[n_sol][theta_vals] = sol

        self.n_eval[n_sol] += 1

        for n, v in enumerate(self.variables):
            v.evaluation.setdefault(n_sol, {})

            v.evaluation[n_sol][theta_vals] = sol[n]

        return {v: sol[i] for i, v in enumerate(self.variables)}

    def lb(self, function: V | Func):
        """Finds the lower bound of a variable or function"""
        # set the objective to minimizing the variable
        setattr(self, f"min({function})", inf(function))
        self.opt()

    def ub(self, function: V | Func):
        """Finds the upper bound of a variable or function"""
        # set the objective to maximizing the variable
        setattr(self, f"max({function})", sup(function))
        self.opt()

    def obj(self):
        """Objective Values"""
        if len(self.objectives) == 1:
            return self.objectives[0].X
        return {o: o.X for o in self.objectives}

    # def slack(self):
    #     """Slack in each constraint"""
    #     return {c: c._ for c in self.leqcons()}

    def sol(self, n_sol: int = 0, slack: bool = True, compare=False):
        """Print sol"""

        if not self.optimized:
            return r"Use .opt() to generate solution"

        display(Markdown(rf"# Solution for {self.name}"))

        display(Markdown("<br><br>"))
        display(Markdown(r"## Objective"))

        self.objectives[n_sol].sol()

        display(Markdown("<br><br>"))
        display(Markdown(r"## Variables"))

        for v in self.variable_sets:
            v.sol(n_sol=n_sol, compare=compare)

        # if slack:
        #     display(Markdown("<br><br>"))
        #     display(Markdown(r"## Constraint Slack"))
        #     for c in self.leqcons():
        #         c.sol(n_sol=n_sol, compare=compare)

    def birth_solution(self):
        """Makes a solution object for the program"""

        solution = Solution(self.name + "_solution_" + str(self.n_sol))
        solution.update(self.variables, n_sol=self.n_sol)

        return solution

    # # Displaying the program
    # def latex(self, descriptive: bool = False):
    #     """Display LaTeX"""

    #     for s in self.sets.index:
    #         display(s.latex(True))

    #     for o in self.objectives:
    #         display(o.latex())

    #     if descriptive:
    #         for c in self.cons():
    #             display(c.latex())

    #     else:
    #         for c in self.sets.cons():
    #             display(c.latex())

    #         for c in self.cons():
    #             if not c.parent:
    #                 display(c.latex())

    def show(
        self,
        descriptive: bool = False,
        nncons: bool = False,
        categorical: bool = False,
        category: str = None,
    ):
        """Pretty Print"""

        display(Markdown(rf"# Mathematical Program for {self}"))

        if category:
            categorical = True

        if self.index_sets:
            display(Markdown("<br><br>"))
            display(Markdown(r"## Index Sets"))

            for i in self.index_sets:
                if len(i) != 0 and i.case != ICase.SELF:
                    i.show(True)

        if self.objectives:
            display(Markdown("<br><br>"))
            display(Markdown(r"## Objective"))

            for o in self.objectives:
                o.show()

        if descriptive:

            display(Markdown("<br><br>"))
            display(Markdown(r"## s.t."))

            if categorical:
                # gather the categories if not already done
                categories: dict[str, list[C]] = {}
                fcategories: dict[str, list[Func]] = {}
                for c in self.cons():
                    if c.category not in categories:
                        categories[c.category] = []
                    categories[c.category].append(c)
                if category and category in categories:
                    sorted_categories = [category]
                else:
                    sorted_categories = sorted(categories.keys())
                self.categories = categories

                for f in self.function_sets:
                    if f.category not in fcategories:
                        fcategories[f.category] = []
                    fcategories[f.category].append(f)
                if category and category in fcategories:
                    sorted_fcategories = [category]
                else:
                    sorted_fcategories = sorted(fcategories.keys())
                self.fcategories = fcategories

                for category in sorted_categories:
                    display(Markdown(rf"### {category} Constraints"))
                    for c in categories[category]:
                        c.show()
                for category in sorted_fcategories:
                    display(Markdown(rf"### {category} Functions"))
                    for f in fcategories[category]:
                        f.show()

            else:

                if self.leqcons():
                    display(Markdown(r"### Inequality Constraints"))
                    for c in self.leqcons():
                        c.show()
                if self.eqcons():
                    display(Markdown(r"### Equality Constraints"))
                    for c in self.eqcons():
                        c.show()

                if self.nncons() and nncons:
                    display(Markdown(r"### Non-Negative Constraints"))
                    for c in self.nncons():
                        c.show()

                if self.functions:
                    display(Markdown("<br><br>"))
                    display(Markdown(r"## Functions"))
                    for f in self.functions:
                        f.show()

        else:

            # if self.sets.nncons():
            #     display(Markdown('<br><br>'))
            #     display(Markdown(r'## Non-Negative Variables'))
            #     self.sets.I_nn.show()

            display(Markdown("<br><br>"))
            display(Markdown(r"## s.t."))

            if categorical:
                # gather the categories if not already done
                categories_sets: dict[str, list[C]] = {}
                fcategories_sets: dict[str, list[Func]] = {}

                for c in self.constraint_sets:
                    if c.category not in categories_sets:
                        categories_sets[c.category] = []
                    categories_sets[c.category].append(c)
                if category and category in categories_sets:
                    sorted_categories = [category]
                else:
                    sorted_categories = sorted(categories_sets.keys())
                self.categories_sets = categories_sets

                for f in self.function_sets:
                    if f.category not in fcategories_sets:
                        fcategories_sets[f.category] = []
                    fcategories_sets[f.category].append(f)
                if category and category in fcategories_sets:
                    sorted_fcategories = [category]
                else:
                    sorted_fcategories = sorted(fcategories_sets.keys())
                self.fcategories_sets = fcategories_sets

                for category in sorted_categories:
                    display(Markdown(rf"### {category} Constraint Sets"))
                    for c in categories_sets[category]:
                        c.show()

                for category in sorted_fcategories:
                    display(Markdown(rf"### {category} Function Sets"))
                    for f in fcategories_sets[category]:
                        f.show()

            else:

                if self.leqcons_sets:
                    display(Markdown("<br><br>"))
                    display(Markdown(r"### Inequality Constraint Sets"))
                    for c in self.leqcons_sets:
                        c.show()
                if self.eqcons_sets:
                    display(Markdown("<br><br>"))
                    display(Markdown(r"### Equality Constraint Sets"))
                    for c in self.eqcons_sets:
                        c.show()

                if self.function_sets:
                    display(Markdown("<br><br>"))
                    display(Markdown(r"## Functions"))
                    for f in self.function_sets:
                        f.show()

    def draw(self, variable: V = None, n_sol: int = 0):
        """Plots the solution for a variable"""
        if n_sol in self.sol_types["MIP"]:
            self.solution[n_sol].draw(variable)
        elif n_sol in self.sol_types["mp"]:
            parametric_plot(self.solution[n_sol])
        else:
            raise ValueError(f"Solution {n_sol} not found")

    # -----------------------------------------------------
    #                    Hashing
    # -----------------------------------------------------

    def __str__(self):
        # return rf"{self.name}"
        return self.name

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(str(self))

    # def __add__(self, other: Self):
    #     """Add two programs"""

    #     if not isinstance(other, Prg):
    #         raise ValueError('Can only add programs')

    #     prg = Prg(name=rf'{self.name}')

    #     for i in (
    #         self.sets.index
    #         + other.sets.index
    #         + self.sets.variable
    #         + other.sets.variable
    #         + self.sets.parameter
    #         + other.sets.parameter
    #     ):
    #         if not i.name in prg.names:
    #             setattr(prg, i.name, i)
    #         else:
    #             if isinstance(i, I) and i.mutable:
    #                 setattr(prg, i.name, getattr(prg, i.name) | i)

    #     for i in (
    #         self.sets.function
    #         + other.sets.function
    #         + self.sets.leqcons()
    #         + self.sets.eqcons()
    #         + other.sets.leqcons()
    #         + other.sets.eqcons()
    #         + self.objectives
    #         + other.objectives
    #     ):
    #         if not i.name in prg.names:
    #             setattr(prg, i.pname, i)

    #     return prg
    # -----------------------------------------------------
    #                    Export
    # -----------------------------------------------------

    def ppopt(self) -> MPLP_Program:
        """Convert the program to a ppopt.MPLP_Program"""

        # A is the matrix of variable coefficients (including nn constraints)
        # b is the RHS vector (including nn constraints)
        # c is the objective coefficients
        # A_t is the critical region A matrix
        # b_t is the critical region RHS vector
        # F is the matrix of theta coefficients (including nn constraints)
        # H are the parameteric objective coefficients

        _A = self.A
        _NN = self.NN
        _B = self.B
        _C = self.C
        _CrA = self.CrA
        _CrB = self.CrB
        _F = self.F

        logger.info(f"Creating PPOPT MPLP_Program for {self}")

        return MPLP_Program(
            A=nparray(_A + _NN),
            b=nparray([[i] for i in _B] + [[0]] * self.n_variables),
            c=nparray([[i] for i in _C]),
            A_t=nparray(_CrA),
            b_t=nparray([[i] for i in _CrB]),
            F=nparray(_F + [[0] * self.n_thetas] * self.n_variables),
            H=npzeros((self.n_variables, self.n_thetas)),
            equality_indices=[c.n for c in self.cons() if c.eq],
        )

    def gurobi(self) -> GPModel:
        """Gurobi Model"""

        self.mps()
        logger.info(f"Creating gurobi model for {self}")
        return gpread(f"{self}.mps")

    # def pyomo(self):
    #     """Pyomo Model"""
    #     if has_pyomo:
    #         m = PyoModel()

    #         for index_set in self.index_sets:
    #             setattr(m, index_set.name, index_set.pyomo())

    #         for v in self.variable_sets:
    #             setattr(m, v.name, v.pyomo())

    #         # for c in self.constraint_sets:

    #         # for c in self.conssets:
    #         #     setattr(m, c.name, c.pyomo(m))

    #         return m
    #     print(
    #         'pyomo is an optional dependency, pip install gana[all] to get optional dependencies'
    #     )
