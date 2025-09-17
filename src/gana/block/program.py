"""Program"""

import warnings
from dataclasses import dataclass, field

from ..sets.cases import PCase, ICase, Elem
from ..sets.constraint import C
from ..sets.function import F as Func
from ..sets.index import I

from ..sets.objective import O
from ..sets.parameter import P
from ..sets.theta import T
from ..sets.variable import V
from .solution import Solution
from ..operators.composition import sup, inf

from ppopt.mplp_program import MPLP_Program
import numpy as np


# optional dependencies
try:
    from gurobipy import read as gpread

    has_gurobi = True
except ImportError:
    has_gurobi = False

try:
    from IPython.display import Markdown, display

    has_ipython = True
except ImportError:
    has_ipython = False

try:
    from pyomo.environ import ConcreteModel as PyoModel

    has_pyomo = True
except ImportError:
    has_pyomo = False


try:
    from pandas import DataFrame

    has_pandas = True
except ImportError:
    has_pandas = False


@dataclass
class Prg:
    """A mathematical program
    Can be a linear (LP), integer (IP), or mixed-integer (MIP)

    Args:
        name (str, optional): Name of the program. Defaults to 'prog'.
        tol (float, optional): Tolerance. Defaults to None.
        canonical (bool, optional): Canonical form. Defaults to True.
        tag (str, optional): Tag for the program. Defaults to ''.

    Attributes:
        names (list[str]): Names of declared sets
        sets (Sets): An object to hold set objects
        names_idx (list[str]): Names of the index elements
        indices (list[X]): Index sets
        variables (list[Var]): Variable sets
        thetas (list[PVar]): Parametric Variable sets
        functions (list[Func]): Function sets
        constraints (list[Cons]): Constraint sets
        objectives (list[Obj]): Objectives

    Raises:
        ValueError: if overwriting a set
    """

    name: str = field(default='prog')
    tol: float = field(default=None)
    canonical: bool = field(default=True)
    tag: str = field(default='')

    def __post_init__(self):

        # ------ collections --------
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

        # ------ names --------
        self.names: list[str] = []  # element names

        self.names_index_sets: list[str] = []  # index sets
        self.names_indices: list[str] = []  # elements
        self.names_variable_sets: list[str] = []  # variable sets
        self.names_parameter_sets: list[str] = []  # parameter sets
        self.names_theta_sets: list[str] = []  # parametric variable sets
        self.names_function_sets: list[str] = []  # function sets
        self.names_constraint_sets: list[str] = []  # constraints
        self.names_objectives: list[str] = []  # objectives

        # ------ counts --------

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
        self.solution: dict[int, Solution] = {}

        # number of solutions
        self.n_sol: int = 0

        # solution matrix

        self.X: dict[int, list[float | int]] = {}

    def add_index(self, name: str, index: I):
        """Adds new index to program

        Args:
            name (str): name of index
            index (I): index set to be added
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
        """Adds indices from an index set to the program

        index (I): Index set who elements are to be added to the program.
        members (list[str]): List of members to be added to the index set.
        """

        if not members:
            # if specific members are not specified
            # add all of them as elements
            members = index.members

        # for unordered sets, the elements are set on the program
        for n, member in enumerate(members):

            if not member in self.names_indices:
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
        """Adds new variable set to program

        Args:
            name (str): name of variable set
            variable (V): variable set to be added
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
        """Mutates an existing variable set in the program
        Args:
            variable_ex (V): exisiting variable set to be mutated
            variable (V): incoming variable set to be added
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
            if not idx in variable_ex.map:
                # set the position of the new variable
                _pos = pos_start + n
                v.pos = _pos
                # set the name based on position in existing variable set
                v.name = f'{_name}[{_pos}]'  # give a name
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
        """Adds new parameter set to program

        Args:
            name (str): name of parameter set
        parameter (P): parameter set to be added
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
        """Mutates an existing parameter set in the program
        Args:
            parameter_ex (P): exisiting parameter set to be mutated
            parameter_new (P): incoming parameter set to be added
        """
        n = 0  # count of parameters added to set
        for idx, p in parameter_new.map.items():

            if idx is None:
                # for a None index, skip
                continue

            if idx in parameter_ex.map:
                # warn if number is being replaced
                warnings.warn(
                    f'The value{parameter_ex.map[idx]} is being overwritten by {p} at index {idx}'
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
        """Adds new theta set to program

        Args:
            name (str): name of theta set
            theta (V): theta set to be added
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
        """Updates the theta set and thetas in a constraint

        Args:
            constraint (C): constraint with thetas to be updated
        """
        for n, theta in enumerate(constraint.function.rhs_thetas):
            self.add_theta(name=f'θ{self.n_theta_sets}', theta=theta)
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
        """Mutates an existing theta set in the program
        Args:
            theta_ex (T): exisiting theta set to be mutated
            theta (T): incoming theta set to be added
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
            if not idx in theta_ex.map:
                # set the position of the new theta
                _pos = pos_start + n
                t.pos = _pos
                # set the name based on position in existing theta set
                t.name = f'{_name}[{_pos}]'  # give a name
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
        """Add a function set to the program

        Args:
            name (str): name of function
            function (F): function object
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
        """Replaces an existing function set in the program

        Args:
            function_ex (F): existing function set to be mutated
            function_new (F): new function set to replace the existing one
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
        """Adds a constraint set to the program

        Args:
            name (str): name of constraint
            constraint (C): constraint object
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
        """Replaces an existing constraint set in the program

        Args:
            constraint_ex (C): existing constraint set to be mutated
            constraint_new (C): new constraint set to replace the existing one
        """
        # just replace the existing constraint set
        # take the old constraints number and pname
        constraint_new.n = constraint_ex.n
        constraint_new.pname = constraint_ex.pname
        if not constraint_ex.category == 'General':

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

        # for variable in self.variable_sets:

        #     if constraint_ex in variable.cons_by:
        #         # if variable is constrained by the old constraint
        #         # remove the constraint from the variable
        #         variable.cons_by[variable.cons_by.index(constraint_ex)] = constraint_new

        #     for var in variable._:

        #         for cons_new, cons_ex in zip(constraint_new._, constraint_ex._):
        #             # if variable is constrained by the old constraint
        #             # update the cons_by list
        #             if cons_ex in var.cons_by:
        #                 var.cons_by[var.cons_by.index(cons_ex)] = cons_new

        # for cons_new in constraint_new._:
        #     # there could be new variables in the updated constraint
        #     for var in cons_new.variables:

        #         # if the variable is in the new constraint
        #         if cons_new not in var.cons_by:

        #             # update the cons_by list
        #             var.cons_by.append(cons_new)

    def add_objective(self, objective: O):
        """Adds an objective set to the program

        Args:
            objective (O): objective object
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

            if not name in self.names_index_sets and not name in self.names_indices:

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

            elif not name in self.names_indices:
                # the set could be already declared, and mutable
                # is being declared as part of another index set
                # in which case get the original set to update
                index_ex: I = getattr(self, name)  # existing index set

                # if not mutable, raise error
                if not index_ex.mutable:
                    raise ValueError(
                        f'{self.name}: Overwriting index {name}. Set mutable=True if index needs to be updated'
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

            if not name in self.names_variable_sets:
                if not value.name in self.names_variable_sets:
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
                        f'{self.name}: Overwriting variable {name}. Set mutable=True if variable needs to be updated'
                    )

                # if an index is being mutated, skip setting
                _mutation = True

                # give a name because
                # the incoming variable set will birth variables too
                # and they will need a name
                value.name = name
                self.mutate_variable(variable_ex, value)

        elif isinstance(value, P):
            if not name in self.names_parameter_sets:
                # if parameter is new, add it to the program

                if value.case in [PCase.NEGSET, PCase.SET]:
                    self.add_parameter(name, value)

            else:
                parameter_ex: P = getattr(self, name)  # existing parameter set

                # if not mutable, raise error
                if not parameter_ex.mutable:
                    raise ValueError(
                        f'{self.name}: Overwriting parameter {name}. Set mutable=True if parameter needs to be updated'
                    )

                # if an index is being mutated, skip setting
                _mutation = True
                # mutate the parameter
                self.mutate_parameter(parameter_ex, value)

        elif isinstance(value, T):

            if not name in self.names_theta_sets:
                self.add_theta(name, value)

            else:
                theta_ex: T = getattr(self, name)
                if not theta_ex.mutable:
                    raise ValueError(
                        f'{self.name}: Overwriting theta {name}. Set mutable=True if theta needs to be updated'
                    )
                _mutation = True
                self.mutate_theta(theta_ex, value)

        elif isinstance(value, Func):
            if not name in self.names_function_sets:
                self.add_function(name, value)
            else:
                # if function is being mutated
                # replace existing function with the new one
                self.replace_function(getattr(self, name), value)
                # but still set it

        elif isinstance(value, C):

            if not name in self.names_constraint_sets:
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

    def intvars(self, n: bool = False) -> list[int | V]:
        """integer variables"""
        if n:
            return [x.n for x in self.variables if x.itg]
        return [x for x in self.variables if x.itg]

    def contvars(self, n: bool = False) -> list[int | V]:
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
            row = [0] * len(self.theta_sets)
            _F.append(row)

        n = 0
        for c in constraints:
            m = 0
            for z, f in zip(c.Z, c.F):
                if z and z[m] is not None:
                    _F[n][z[m]] = f[m]
                m += 1
                n += 1
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

        # TODO multiple objective

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
        """Matrix of Variable coefficients for type:

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
            CrB_.append(t._[1])
            CrB_.append(-t._[0])

        return CrB_

    def make_A_df(self, longname: bool = False) -> DataFrame:
        """Create a DataFrame from the A matrix.

        Args:
            longname (bool, optional): Whether to use long names for variables. Defaults to False.

        Returns:
            DataFrame: Columns are the variables, rows are the constraints.
        """
        if not has_pandas:
            raise ImportError("pip install gana[all] to get optional dependencies")
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
        """Create a DataFrame from the B vector.

        Args:
            longname (bool, optional): Whether to use long names for variables. Defaults to False.

        Returns:
            DataFrame: Has a single column, rows are the constraints.
        """
        if not has_pandas:
            raise ImportError("pip install gana[all] to get optional dependencies")
        if longname:
            index = [c.longname for c in self.cons()]
        else:
            index = [c.name for c in self.cons()]

        return DataFrame(self.B, columns=['RHS'], index=index)

    def make_C_df(self, longname: bool = False) -> DataFrame:
        """Create a DataFrame from the C matrix.

        Args:
            longname (bool, optional): Whether to use long names for variables. Defaults to False.

        Returns:
            DataFrame: Columns are the variables, Has a single row
        """
        if not has_pandas:
            raise ImportError("pip install gana[all] to get optional dependencies")

        if longname:
            columns = [v.longname for v in self.variables]
        else:
            columns = [v.name for v in self.variables]
        return DataFrame([self.C], columns=columns, index=['Minimize'])

    def make_df(self, longname: bool = False) -> DataFrame:
        """Create a DataFrame from the model.

        Args:
            longname (bool, optional): Whether to use long names for variables. Defaults to False.

        Returns:
            DataFrame: A DataFrame with the A matrix, B vector, and C vector.
        """
        if not has_pandas:
            raise ImportError("pip install gana[all] to get optional dependencies")
        if longname:
            index = ['Minimize'] + [c.longname for c in self.cons()]
            columns = [v.longname for v in self.variables] + ['RHS']
        else:
            index = ['Minimize'] + [c.name for c in self.cons()]
            columns = [v.name for v in self.variables] + ['RHS']
        data = []
        for n, d in enumerate(self.A):
            d.append(self.B[n])
            data.append(d)

        data = [self.C + [0]] + data

        return DataFrame(data, columns=columns, index=index)

    def make_CrA_df(self, longname: bool = False) -> DataFrame:
        """Creates a DataFrame from the Critical Region A matrix."""
        if not has_pandas:
            raise ImportError("pip install gana[all] to get optional dependencies")

        if longname:
            columns = [t.longname for t in self.thetas]
            index = sum([[t.longname] * 2 for t in self.thetas], [])
        else:
            columns = [t.name for t in self.thetas]
            index = sum([[t.name] * 2 for t in self.thetas], [])

        return DataFrame(self.CrA, columns=columns, index=index)

    def make_CrB_df(self, longname: bool = False) -> DataFrame:
        """Creates a DataFrame from the Critical Region RHS vector."""
        if not has_pandas:
            raise ImportError("pip install gana[all] to get optional dependencies")

        if longname:
            index = sum([[t.longname] * 2 for t in self.thetas], [])
        else:
            index = sum([[t.name] * 2 for t in self.thetas], [])

        return DataFrame(self.CrB, columns=['RHS'], index=index)

    def make_F_df(self, longname: bool = False) -> DataFrame:
        """Creates a DataFrame from the Theta coefficients matrix."""
        if not has_pandas:
            raise ImportError("pip install gana[all] to get optional dependencies")

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

        print(f'--- Generating {name or self.name}.mps')

        # 1 unit of whitespace
        ws = ' '
        # renumber the constraints based on order in .cons()
        # as opposed to order of declaration
        self.renumber()

        leq_cons = self.leqcons()
        eq_cons = self.eqcons()
        cont_vars = self.contvars()
        nn_vars = self.nnvars()
        bnr_vars = self.bnrvars()

        # _C = self.C
        # _A = self.A

        # write the MPS file
        with open(f'{name or self.name}.mps', 'w', encoding='utf-8') as f:

            # header: NAME          MODEL_NAME
            f.write(f'NAME{ws*10}{self.name.upper()}\n')

            # Here the constraint types are defined
            f.write('ROWS\n')

            if self.objectives:
                # the objective is: N   OBJECTIVE_NAME
                f.write(f'{ws}N{ws*3}{self.objectives[-1].mps()}\n')

            for c in leq_cons:
                # less than or equal constraints are: L   CONSTRAINT_NAME
                f.write(f'{ws}L{ws*3}{c.mps()}\n')

            for c in eq_cons:
                # equality constraints are: E   CONSTRAINT_NAME
                f.write(f'{ws}E{ws*3}{c.mps()}\n')

            # Here the variables are defined along with their coefficients
            # in each of the constraints that they feature in

            f.write('COLUMNS\n')
            for v in self.variables:
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
                    # if isinstance(c, O):
                    #     f.write(f'{c.function[0].matrix[v.n]}')
                    # else:
                    #     f.write(f'{c.matrix[v.n]}')
                    f.write(f'{c.matrix[v.n]}')

                    # f.write(f'{c.A[c.P.index(v.n)]}')

                    f.write('\n')

                for o in v.min_by:
                    # this captures the length of the variable name
                    # variable names are just Vn where n is order of precedence
                    vfs = len(o.mps())
                    f.write(ws * 4)
                    f.write(v.mps())
                    f.write(ws * (10 - vs))
                    f.write(o.mps())
                    f.write(ws * (10 - vfs))

                    f.write(f'{o.function[0].matrix[v.n]}')

                    # f.write(f'{c.A[c.P.index(v.n)]}')
                    f.write('\n')

            # This gives the right-hand side of the constraints
            f.write('RHS\n')
            for n, c in enumerate(leq_cons + eq_cons):
                # For each constraint, we write:
                # RHSn    CONSTRAINT_NAME    RHS_VALUE
                f.write(ws * 4)
                f.write(f'RHS{n}')
                f.write(ws * (10 - len(f'RHS{n+1}')))
                f.write(c.mps())
                f.write(ws * (10 - len(c.mps())))
                f.write(f'{c.B}')
                f.write('\n')

            f.write('BOUNDS\n')
            # for continuous variables that are nonnegative, we write:
            # LO BND1    VARIABLE_NAME    0
            for v in nn_vars:
                if v in cont_vars:
                    f.write(f'{ws}LO{ws}BND1{ws*4}{v.mps()}{ws*8}{0}\n')

            # for integer variables that are binary, we write:
            # BV BND1    VARIABLE_NAME
            for v in bnr_vars:
                f.write(f'{ws}BV{ws}BND1{ws*5}{v.mps()}\n')

            # CLOSE the MPS file
            f.write('ENDATA')

    def lp(self):
        """LP File"""
        m = self.gurobi()
        m.write(f'{self.name}.lp')

    # --------------------------------------------------
    #               Optimize
    # --------------------------------------------------
    def opt(self, using: str = 'gurobi'):
        """Solve the program"""

        if using == 'gurobi':
            m = self.gurobi()

            print(f'--- Optimizing {self} using {using}')
            m.optimize()
            try:
                print('--- Solution found. Use .sol() to display it')

                self.X[self.n_sol] = [v.X for v in m.getVars()]

                for v, val in zip(self.variables, self.X[self.n_sol]):

                    v.X[self.n_sol] = val

                for c in self.constraint_sets:
                    c.function.eval(n_sol=self.n_sol)

                self.objectives[-1].X = m.ObjVal
                self.optimized = True

                print('--- Creating Solution object, check.solution')

                self.solution[self.n_sol] = self.birth_solution()

                self.n_sol += 1

            except AttributeError:
                print('!!! No solution found. Check the model.')

    def lb(self, function: V | Func):
        """Finds the lower bound of a variable or function"""
        # set the objective to minimizing the variable
        setattr(self, f'min({function})', inf(function))
        self.opt()

    def ub(self, function: V | Func):
        """Finds the upper bound of a variable or function"""
        # set the objective to maximizing the variable
        setattr(self, f'max({function})', sup(function))
        self.opt()

    def obj(self):
        """Objective Values"""
        if len(self.objectives) == 1:
            return self.objectives[0].X
        return {o: o.X for o in self.objectives}

    # def slack(self):
    #     """Slack in each constraint"""
    #     return {c: c._ for c in self.leqcons()}

    def sol(self, n_sol: int = 0, slack: bool = True):
        """Print sol"""

        if not self.optimized:
            return r'Use .opt() to generate solution'

        display(Markdown(rf'# Solution for {self.name}'))

        print()
        display(Markdown(r'## Objective'))
        for o in self.objectives:
            o.sol()

        print()
        display(Markdown(r'## Variables'))

        for v in self.variable_sets:
            v.sol(n_sol=n_sol)

        if slack:
            print()
            display(Markdown(r'## Constraint Slack'))
            for c in self.leqcons():
                c.sol(n_sol=n_sol)

    def birth_solution(self):
        """Makes a solution object for the program"""

        solution = Solution(self.name + '_solution_' + str(self.n_sol))
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

        display(Markdown(rf'# Mathematical Program for {self}'))

        if category:
            categorical = True

        if self.index_sets:
            print()
            display(Markdown(r'## Index Sets'))

            for i in self.index_sets:
                if len(i) != 0 and i.case != ICase.SELF:
                    i.show(True)

        if self.objectives:
            print()
            display(Markdown(r'## Objective'))

            for o in self.objectives:
                o.show()

        if descriptive:

            print()
            display(Markdown(r'## s.t.'))

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
                    display(Markdown(rf'### {category} Constraints'))
                    for c in categories[category]:
                        c.show()
                for category in sorted_fcategories:
                    display(Markdown(rf'### {category} Functions'))
                    for f in fcategories[category]:
                        f.show()

            else:

                if self.leqcons():
                    display(Markdown(r'### Inequality Constraints'))
                    for c in self.leqcons():
                        c.show()
                if self.eqcons():
                    display(Markdown(r'### Equality Constraints'))
                    for c in self.eqcons():
                        c.show()

                if self.nncons() and nncons:
                    display(Markdown(r'### Non-Negative Constraints'))
                    for c in self.nncons():
                        c.show()

                if self.functions:
                    print()
                    display(Markdown(r'## Functions'))
                    for f in self.functions:
                        f.show()

        else:

            # if self.sets.nncons():
            #     print()
            #     display(Markdown(r'## Non-Negative Variables'))
            #     self.sets.I_nn.show()

            print()
            display(Markdown(r'## s.t.'))

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
                    display(Markdown(rf'### {category} Constraint Sets'))
                    for c in categories_sets[category]:
                        c.show()

                for category in sorted_fcategories:
                    display(Markdown(rf'### {category} Function Sets'))
                    for f in fcategories_sets[category]:
                        f.show()

            else:

                if self.leqcons_sets:
                    print()
                    display(Markdown(r'### Inequality Constraint Sets'))
                    for c in self.leqcons_sets:
                        c.show()
                if self.eqcons_sets:
                    print()
                    display(Markdown(r'### Equality Constraint Sets'))
                    for c in self.eqcons_sets:
                        c.show()

                if self.function_sets:
                    print()
                    display(Markdown(r'## Functions'))
                    for f in self.function_sets:
                        f.show()

    def draw(self, variable: V, n_sol: int = 0):
        """Plots the solution for a variable"""
        self.solution[n_sol].draw(variable)

    # -----------------------------------------------------
    #                    Hashing
    # -----------------------------------------------------

    def __str__(self):
        return rf'{self.name}'

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

        return MPLP_Program(
            A=np.array(self.A + self.NN),
            b=np.array([[i] for i in self.B] + [[0]] * self.n_variables),
            c=np.array([[i] for i in self.C]),
            A_t=np.array(self.CrA),
            b_t=np.array([[i] for i in self.CrB]),
            F=np.array(self.F + [[0] * self.n_thetas] * self.n_variables),
            H=np.zeros((self.n_variables, self.n_thetas)),
            equality_indices=[c.n for c in self.cons() if c.eq],
        )

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

    def gurobi(self):
        """Gurobi Model"""

        self.mps()
        print(f'--- Creating gurobi model for {self}')
        return gpread(f'{self}.mps')
