"""Program"""

import json
import logging
import pickle
import warnings
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, cast, overload

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
from scipy.sparse import csr_matrix

from gana.types import Number

from ..backends.native import registry as native_registry
from ..backends.native.constraints import compile_program
from ..backends.native.export import build as build_native_export
from ..backends.native.export import renumber as renumber_native_export
from ..backends.native.results import load as load_native_results
from ..backends.native.theta import register_pending
from ..operators.composition import inf, sup
from ..sets.cases import ICase
from ..sets.constraint import C
from ..sets.function import F as Func
from ..sets.index import I
from ..sets.objective import O
from ..sets.parameter import P
from ..sets.theta import T
from ..sets.variable import V
from ..storage import parameters as storage
from ..storage import symbols as symbol_storage
from ..utils.decorators import timer
from .solution import Solution

logger = logging.getLogger("gana")
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


# Keep renderer row types at module scope: Prg.C is the objective vector.
type _DisplayItem = C | Func | V
type _DisplaySection = tuple[int, str, Sequence[_DisplayItem]]


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
    # None preserves the solver's default tolerance until explicitly set.
    tol: float | None = field(default=None)
    canonical: bool = field(default=True)
    tag: str = field(default="")

    def __post_init__(self):
        """Initialize independent registration and solve-history containers."""

        # Identity-only binding survives pickle without retaining this program.
        self._owner_token = object()

        # ---collections --------
        # index (I)
        self.index_sets: list[I] = []
        self.indices: list[I] = []

        # variable (V)
        self.variable_sets: list[V] = []
        self.variables: Sequence[V] = (
            symbol_storage.SymbolRegistry() if storage.NATIVE else []
        )

        # parameter (P)
        self.parameter_sets: list[P] = []  # parameter sets
        # parameter set elements are just numeric

        # parametric variable (T)
        self.theta_sets: list[T] = []
        self.thetas: Sequence[T] = (
            symbol_storage.SymbolRegistry() if storage.NATIVE else []
        )

        # function (F)
        # Scalar variable objectives also retain their original display node.
        self.function_sets: list[Func | V] = []
        self.functions: list[Func] | symbol_storage.SymbolRegistry = (
            symbol_storage.SymbolRegistry() if storage.NATIVE else []
        )

        # constraint (C)
        self.constraint_sets: list[C] = []
        self.constraints: list[C] | symbol_storage.SymbolRegistry = (
            symbol_storage.SymbolRegistry() if storage.NATIVE else []
        )

        self.categories_sets: dict[
            str,
            list[C],
        ] = {}  # categories of constraint sets
        self.categories: dict[str, list[C]] = {}  # categories of constraints

        self.fcategories_sets: dict[
            str,
            list[Func | V],
        ] = {}  # categories of function sets
        self.fcategories: dict[str, list[Func | V]] = {}

        # objective (O)
        self.objectives: list[O] = []

        # ---names --------
        self.names: list[str | None] = []  # includes unnamed objectives

        self.names_index_sets: list[str] = []  # index sets
        self.names_indices: list[str] = []  # elements
        self.names_variable_sets: list[str] = []  # variable sets
        self.names_parameter_sets: list[str] = []  # parameter sets
        self.names_theta_sets: list[str] = []  # parametric variable sets
        self.names_function_sets: list[str] = []  # function sets
        self.names_constraint_sets: list[str] = []  # constraints
        self.names_objectives: list[str | None] = []  # may be unnamed

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
        self.solutions: dict[int, Solution | MPSolution] = {}

        # number of solutions
        self.n_solutions: int = 0

        # solution matrix
        self.X: dict[int, list[Number | None]] = {}

        # formulations available
        self.formulations: dict[int, GPModel | MPLP_Program] = {}

        # number of formulations
        self.n_formulations: int = 0

        # evaluations using parametric solutions
        self.evaluation: dict[int, dict[tuple[float, ...], list[float]]] = {}

        # number of evaluations by solution number
        self.n_evaluation: dict[int, int] = {}

        # solution types
        self.sol_types: dict[str, list[int]] = {"MIP": [], "mp": []}

    @property
    def solution(self) -> Solution | MPSolution | None:
        """
        Returns the latest solution of the program

        :returns: Latest solution, or None before any solve.
        :rtype: Solution | MPSolution | None
        """
        if self.n_solutions > 0:
            return list(self.solutions.values())[-1]
        return None

    @property
    def formulation(self) -> GPModel | MPLP_Program | None:
        """
        Returns the latest formulation of the program

        :returns: Latest formulation, or None before any formulation.
        :rtype: GPModel | MPLP_Program | None
        """
        if self.n_formulations > 0:
            return list(self.formulations.values())[-1]
        return None

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

    def add_indices(
        self, index: I, members: Sequence[str | int | I] | None = None
    ):
        """
        Adds indices from an index set to the program

        :param index: Index set who elements are to be added to the program.
        :type index: I
        :param members: Labels or existing members to add to the index set.
        :type members: Sequence[str | int | I], optional
        """

        if not members:
            # if specific members are not specified
            # add all of them as elements
            members = index.members

        # for unordered sets, the elements are set on the program
        for raw_member in members:
            member = str(raw_member)
            if member in self.names_indices:
                # if this element has not been added to the program before
                # create an element set
                # if the element is already set on the program
                # it can be part of another set already, get it from the
                # program
                # e.g. human is both part of the kingdom index set animalia
                # and the family set hominidae
                # so its parent sets need to be animalia as well as hominidae
                # so update parent and add position in the new index set
                element = cast(I, getattr(self, member))
                # these should not be set again
                _new_elm = False
            else:
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

            # update the index (I) as a parent
            # Named members keep a list of axes; sliced sets instead retain
            # a single source parent and do not enter this registration path.
            cast("list[I]", element.parent).append(index)
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

    def _bound_here(self, element: P | V | T) -> bool:
        """
        Reject foreign roots and selections before any registration changes.
        """
        token = getattr(element._owner_root, "_program_token", None)
        if token is not None and token is not self._owner_token:
            message = "Element belongs to another program"
            raise ValueError(message)
        return token is self._owner_token

    def _bind_element(self, name: str, element: P | V | T) -> None:
        """
        Bind a fully prepared owner without a reference back to the program.
        """
        element._program_token = self._owner_token
        element._registration_name = name
        # Initialize V's slot once, avoiding an AttributeError on every
        # selection.
        element._selection_owner = None
        self.names.append(name)
        self.optimized = False

    def _check_new_owner(self, name: str, element: P | V | T) -> bool:
        """
        Allow aliases, but reject a new root under an occupied registry name.
        """
        if self._bound_here(element):
            return False
        if element._owner_root is not element:
            message = "Register the owner before registering its selection"
            raise ValueError(message)
        if name in self.names:
            message = f"The name {name} is already registered"
            raise ValueError(message)
        return True

    def _check_update(self, existing: P | V | T, incoming: P | V | T) -> None:
        """
        Validate mutation authority before allocating or changing storage.
        """
        if not self._bound_here(existing):
            message = "Mutation requires an owner registered in this program"
            raise ValueError(message)
        if existing._owner_root is not existing:
            message = "Mutation through a selection is not supported"
            raise ValueError(message)
        if not existing.mutable:
            message = "Overwriting an element requires mutable=True"
            raise ValueError(message)
        if self._bound_here(incoming):
            message = "Mutation requires a fresh declaration"
            raise ValueError(message)
        if incoming._owner_root is not incoming:
            message = "Mutation requires a fresh owner, not a selection"
            raise ValueError(message)

    def add_variable(self, name: str, variable: V):
        """
        Register one owner after preparing its scalar members exactly once.
        """
        if not self._check_new_owner(name, variable):
            return
        variable._implicit_index(1)
        variable.name = name
        variable.birth_variables(n_start=self.n_variables)
        variable.n = self.n_variable_sets
        self._bind_element(name, variable)
        self.names_variable_sets.append(name)
        self.variable_sets.append(variable)
        self._register_members(self.variables, variable)
        self.n_variable_sets += 1
        self.n_variables += len(variable)

    @staticmethod
    def _register_members(registry, root, start=0):
        """Register native owner spans lazily; preserve legacy Python lists."""
        if isinstance(registry, symbol_storage.SymbolRegistry):
            registry.add(root, start)
        else:
            registry.extend(root._ if not start else root._[start:])

    def _grow_native_symbols(
        self,
        root,
        incoming,
        keys,
        *,
        start,
        registry,
        bounds=None,
    ):
        """
        Commit native growth and its global registry span without creating
        wrappers.
        """
        if not keys:
            return 0
        old_length = len(root)
        index = root._merged_index(incoming)
        root._symbol_storage.append(keys, start, bounds)
        root.index = index
        root.n_splices += 1
        self._register_members(registry, root, old_length)
        self.optimized = False
        return len(keys)

    def mutate_variable(self, variable_ex: V, variable_new: V):
        """Append only new coordinates, assigning contiguous global IDs."""
        self._check_update(variable_ex, variable_new)
        old_domain = (variable_ex.itg, variable_ex.nn, variable_ex.bnr)
        new_domain = (variable_new.itg, variable_new.nn, variable_new.bnr)
        if old_domain != new_domain:
            message = "Variable growth must preserve the owner's domain"
            raise ValueError(message)
        keys = [
            key
            for key in variable_new.map
            if key is not None and key not in variable_ex.map
        ]
        if hasattr(variable_ex, "_symbol_storage"):
            self.n_variables += self._grow_native_symbols(
                variable_ex,
                variable_new,
                keys,
                start=self.n_variables,
                registry=self.variables,
            )
            return
        index = variable_ex._merged_index(variable_new)
        members = [
            variable_ex._new_member(
                key,
                len(variable_ex) + offset,
                self.n_variables + offset,
            )
            for offset, key in enumerate(keys)
        ]
        if members:
            variable_ex.map.update(zip(keys, members))
            variable_ex._.extend(members)
            variable_ex.index = index
            variable_ex.n_splices += 1
            self._register_members(
                self.variables,
                variable_ex,
                len(variable_ex) - len(members),
            )
            self.n_variables += len(members)
            self.optimized = False

    def add_parameter(self, name: str, parameter: P):
        """
        Register constants and indexed parameters after validating storage.
        """
        if not self._check_new_owner(name, parameter):
            return
        parameter._validated_values(collect=False)
        storage.register(parameter)
        if not parameter.name:
            parameter.name = name
        parameter.n = self.n_parameter_sets
        self._bind_element(name, parameter)
        self.names_parameter_sets.append(name)
        self.parameter_sets.append(parameter)
        self.n_parameter_sets += 1

    @staticmethod
    def _refresh_parameter_case(parameter: P) -> None:
        """
        Invalidate numeric shortcuts when an updated constant becomes a set.
        """
        storage.refresh_case(parameter)

    @staticmethod
    def _parameter_update_values(existing: P, incoming: P) -> dict:
        """
        Match indexless payloads by position; explicit domains use their keys.
        """
        values = incoming._validated_values()
        if not (
            getattr(existing, "_implicit_coordinates", False)
            and getattr(incoming, "_implicit_coordinates", False)
        ):
            return values
        old_keys = list(existing.map)
        return {
            old_keys[pos] if pos < len(old_keys) else key: value
            for pos, (key, value) in enumerate(values.items())
        }

    def mutate_parameter(self, parameter_ex: P, parameter_new: P):
        """
        Stage ordered replacement and growth; warnings may abort before commit.

        Previously formed expressions and partial P selections retain their
        captured values. Successful updates preserve the registered owner.
        """
        self._check_update(parameter_ex, parameter_new)
        staged = parameter_ex._validated_values()
        incoming = self._parameter_update_values(parameter_ex, parameter_new)
        growing = any(key not in staged for key in incoming)
        index = (
            parameter_ex._merged_index(parameter_new)
            if growing
            else parameter_ex.index
        )
        for key, value in incoming.items():
            if key in staged:
                warnings.warn(
                    f"The value {staged[key]} is being overwritten by {value} "
                    f"at index {key}",
                    stacklevel=2,
                )
        staged.update(incoming)
        storage.replace(parameter_ex, staged)
        parameter_ex.index = index
        parameter_ex.n_splices += int(growing)
        self._refresh_parameter_case(parameter_ex)
        self.optimized = False

    def add_theta(self, name: str, theta: T):
        """
        Register a theta owner only after its full bounds payload validates.
        """
        if not self._check_new_owner(name, theta):
            return
        bounds = theta._validated_bounds()
        theta.name = theta._derived_name or name
        theta._birth_validated(bounds, n_start=self.n_thetas)
        theta.n = self.n_theta_sets
        self._bind_element(name, theta)
        self.names_theta_sets.append(name)
        self.theta_sets.append(theta)
        self._register_members(self.thetas, theta)
        self.n_theta_sets += 1
        self.n_thetas += len(theta)

    def update_theta(self, constraint: C):
        """Resolve retained owner/coordinate terms into shared theta columns.

        Construction records RHS signs and coefficients independently of tree
        shape. Register anonymous roots once, then resolve each scalar row;
        never replace expression operands or create scaled interval owners.
        """
        function = constraint.function
        if not isinstance(function, Func):
            return
        for theta in function.rhs_thetas:
            if not self._bound_here(theta):
                self.add_theta(name=f"θ{self.n_theta_sets}", theta=theta)
        for row in constraint:
            terms = row.function._theta_terms
            row.function.F = [a for _, _, a in terms]
            row.function.Z = [owner.map[key].n for owner, key, _ in terms]
        if function.parent is None:
            # Constraint iteration yields scalar rows, not their collections.
            function.F = [
                cast("list[Number]", row.function.F) for row in constraint
            ]
            function.Z = [
                cast("list[int | None]", row.function.Z) for row in constraint
            ]

    def mutate_theta(self, theta_ex: T, theta_new: T):
        """
        Append accepted theta coordinates, preserving old bounds and identity.
        """
        self._check_update(theta_ex, theta_new)
        bounds = theta_new._validated_bounds()
        accepted = [
            (key, pair)
            for key, pair in zip(theta_new.map, bounds)
            if key is not None and key not in theta_ex.map
        ]
        if hasattr(theta_ex, "_symbol_storage"):
            self.n_thetas += self._grow_native_symbols(
                theta_ex,
                theta_new,
                [key for key, _ in accepted],
                start=self.n_thetas,
                registry=self.thetas,
                bounds=[pair for _, pair in accepted],
            )
            return
        index = theta_ex._merged_index(theta_new)
        members = [
            theta_ex._new_member(
                key,
                len(theta_ex) + offset,
                self.n_thetas + offset,
                pair,
            )
            for offset, (key, pair) in enumerate(accepted)
        ]
        if members:
            theta_ex.map.update(
                (key, member) for (key, _), member in zip(accepted, members)
            )
            theta_ex._.extend(members)
            theta_ex.index = index
            theta_ex.n_splices += 1
            self._register_members(
                self.thetas,
                theta_ex,
                len(theta_ex) - len(members),
            )
            self.n_thetas += len(members)
            self.optimized = False

    def add_function(self, name: str, function: Func):
        """
        Add a function set to the program

        :param name: name of function
        :type name: str
        :param function: function object
        :type function: F
        """
        self._check_expression_owners(function)
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

        # Native spans record membership without constructing scalar rows.
        if isinstance(self.functions, symbol_storage.SymbolRegistry):
            self.functions.add(function)
        else:
            # Registration requires populated rows; numbering still raises on
            # incomplete expressions instead of silently dropping placeholders.
            self.functions.extend(cast("list[Func]", function._))
        self._number_function_rows(function, self.n_functions)
        self.n_functions += len(function)

    @staticmethod
    def _number_function_rows(function, start):
        """Defer row numbers until native members are requested."""
        if (
            "_native_batch" in function.__dict__
            or "_native_registered" in function.__dict__
        ) and "_legacy_cache" not in function.__dict__:
            function._native_number_start = start
            return
        for position, row in enumerate(function):
            row.n = start + position

    @staticmethod
    def _replace_registered(items, old, new):
        """
        Replace members at their first slot using identity, never symbolic ==.

        Export row numbers are temporary and cannot serve as list positions.
        Preserve unrelated members when the replacement has a different size.
        """
        removed = {id(item) for item in old}
        position = next(
            n for n, item in enumerate(items) if id(item) in removed
        )
        items[position:] = list(new) + [
            item for item in items[position:] if id(item) not in removed
        ]

    def replace_function(self, function_ex: Func, function_new: Func):
        """
        Replace registered expressions by identity and renumber their members.

        Objective registrations belong to objective objects, not expressions;
        existing objectives continue to reference their original expression.
        """
        self._check_expression_owners(function_new)
        function_new.n = function_ex.n
        function_new.pname = function_ex.pname
        self._replace_registered(
            self.function_sets,
            [function_ex],
            [function_new],
        )
        if isinstance(self.functions, symbol_storage.SymbolRegistry):
            self.functions = list(self.functions)
        self._replace_registered(self.functions, function_ex._, function_new._)
        for number, function in enumerate(self.functions):
            function.n = number
        self.n_functions = len(self.functions)

    def add_constraint(self, name: str, constraint: C):
        """
        Adds a constraint set to the program

        :param name: name of constraint
        :type name: str
        :param constraint: constraint object
        :type constraint: C
        """
        self._check_expression_owners(constraint.function)
        # Validate anonymous owners before bookkeeping, while keeping the
        # public name order: the constraint precedes its generated thetas.
        name_position = len(self.names)
        register_pending(self, constraint.function, constraint_name=name)
        self.names.insert(name_position, name)
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

        # Preserve batch spans until callers explicitly request scalar rows.
        if isinstance(self.constraints, symbol_storage.SymbolRegistry):
            self.constraints.add(constraint)
        else:
            self.constraints.extend(constraint._)
        self._number_function_rows(constraint, self.n_constraints)

        # update the number of constraints
        self.n_constraints += len(constraint)

        if self._constraint_has_thetas(constraint):
            # if the constraint has thetas in them
            # then update the thetas in the function
            self.update_theta(constraint)

    @staticmethod
    def _constraint_has_thetas(constraint):
        """Legacy constraints bind theta rows even after native replay."""
        function = constraint.function
        if "_native_registered" in constraint.__dict__:
            return False
        return bool(getattr(function, "rhs_thetas", ()))

    def replace_constraint(self, constraint_ex: C, constraint_new: C):
        """
        Replace rows by identity, rebuilding affected variable registrations.
        """
        self._check_expression_owners(constraint_new.function)
        register_pending(self, constraint_new.function)
        constraint_new.n = constraint_ex.n
        constraint_new.pname = constraint_ex.pname
        if constraint_ex.category != "General":
            constraint_new.categorize(constraint_ex.category)
        self._replace_registered(
            self.constraint_sets,
            [constraint_ex],
            [constraint_new],
        )
        self._replace_constraint_rows(constraint_ex, constraint_new)
        constraint_ex.unregister_variables()
        constraint_new.update_variables()
        self.n_constraints = len(self.constraints)
        self.renumber()
        if self._constraint_has_thetas(constraint_new):
            self.update_theta(constraint_new)

    def _replace_constraint_rows(self, old, new):
        """Keep independent spans, with a list fallback for shared rows."""
        registry = native_registry.replacement(self.constraints, old, new)
        if registry is not None:
            self.constraints = registry
            return
        if isinstance(self.constraints, symbol_storage.SymbolRegistry):
            self.constraints = list(self.constraints)
        self._replace_registered(self.constraints, old._, new._)

    def add_objective(self, objective: O):
        """
        Activate the newest objective and retain older objects as solve
        history.

        :param objective: objective object
        :type objective: O
        """
        self._check_expression_owners(objective.function)
        if self.active_objective is not None:
            self.active_objective.unregister_variables()
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

    @property
    def active_objective(self) -> O | None:
        """Return the newest objective, shared by matrix and export paths."""
        return self.objectives[-1] if self.objectives else None

    def _assign_index(self, name: str, value: I) -> bool:
        """
        Preserve named, ordered and mutable index registration conventions.
        """
        if self.__dict__.get(name) is value:
            return False
        if name in self.names_indices:
            return True
        if name in self.names_index_sets:
            self._extend_index(getattr(self, name), value)
            return False
        self.add_index(name, value)
        if len(value.members) == 1 and value.members[0] == name:
            value._ = [value]
            value.case = ICase.SELF
        elif value.ordered:
            value.birth_elements()
        else:
            self.add_indices(value)
        return True

    def _extend_index(self, existing: I, incoming: I) -> None:
        """
        Append missing unordered members, retaining the existing index owner.
        """
        if not existing.mutable:
            message = "Overwriting an index requires mutable=True"
            raise ValueError(message)
        if not incoming.ordered:
            members = [
                member
                for member in incoming.members
                if member not in existing.members
            ]
            if members:
                self.add_indices(existing, members)

    def _assign_element(self, name: str, value: P | V | T) -> bool:
        """Handle same-program aliases and updates before new registrations."""
        bound = self._bound_here(value)
        # Energia creates indices in __getattr__; probing must have no side
        # effects.
        existing = self.__dict__.get(name)
        if existing is value:
            return False
        if isinstance(existing, (P, V, T)):
            if type(existing) is not type(value):
                message = "Cannot change the kind of a registered element"
                raise ValueError(message)
            self._mutate_element(existing, value)
            return False
        if not bound:
            self._register_element(name, value)
        return True

    def _register_element(self, name: str, value: P | V | T) -> None:
        """Dispatch fresh roots with concrete constructor types."""
        if isinstance(value, P):
            self.add_parameter(name, value)
        elif isinstance(value, V):
            self.add_variable(name, value)
        else:
            self.add_theta(name, value)

    def _mutate_element(self, existing: P | V | T, value: P | V | T) -> None:
        """
        Dispatch an update after the assignment check proves matching kinds.
        """
        if isinstance(value, P):
            self.mutate_parameter(cast(P, existing), value)
        elif isinstance(value, V):
            self.mutate_variable(cast(V, existing), value)
        else:
            self.mutate_theta(cast(T, existing), value)

    def _check_expression_owners(self, function) -> None:
        """
        Reject foreign symbolic operands before bookkeeping touches variables.

        Anonymous theta intervals remain supported by constraint registration.
        Numerical coefficients have already been captured by the expression.
        """
        owners = function.__dict__.get("_native_owners")
        variables = (
            [owner.root for owner in owners if not isinstance(owner.root, T)]
            if owners is not None
            else function.variables
        )
        for variable in variables:
            if not self._bound_here(variable):
                message = "Register variables before using them in expressions"
                raise ValueError(message)
        thetas = (
            [owner.root for owner in owners if isinstance(owner.root, T)]
            if owners is not None
            else getattr(function, "rhs_thetas", [])
        )
        for theta in thetas:
            self._bound_here(theta)

    def _assign_function(self, name: str, value: Func) -> None:
        """
        Register or replace a function only after checking operand ownership.
        """
        if name in self.names_function_sets:
            self.replace_function(getattr(self, name), value)
        else:
            self.add_function(name, value)

    def _assign_constraint(self, name: str, value: C) -> None:
        """
        Register or replace a constraint without accepting foreign columns.
        """
        if name in self.names_constraint_sets:
            self.replace_constraint(getattr(self, name), value)
        else:
            self.add_constraint(name, value)

    def __setattr__(self, name, value) -> None:
        """
        Dispatch registrations; mutations preserve the existing root attribute.
        """
        store = True
        if isinstance(value, I):
            store = self._assign_index(name, value)
        elif isinstance(value, (P, V, T)):
            store = self._assign_element(name, value)
        elif isinstance(value, Func):
            self._assign_function(name, value)
        elif isinstance(value, C):
            self._assign_constraint(name, value)
        elif isinstance(value, O):
            self.add_objective(value)
        if store:
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
        """Return nonnegativity rows or their assigned program row numbers."""
        if n:
            return [cast(int, x.n) for x in self.constraints if x.nn]
        return [x for x in self.constraints if x.nn]

    @overload
    def eqcons(self, n: Literal[False] = False) -> list[C]:
        """Return equality rows by default."""
        ...

    @overload
    def eqcons(self, n: Literal[True]) -> list[int]:
        """Return assigned equality row numbers when requested."""
        ...

    @overload
    def eqcons(self, n: bool) -> list[int] | list[C]:
        """Support a dynamically selected representation."""
        ...

    def eqcons(self, n: bool = False) -> list[int] | list[C]:
        """Return equality rows or their assigned program row numbers."""
        if n:
            return [cast(int, x.n) for x in self.constraints if not x.leq]
        return [x for x in self.constraints if not x.leq]

    @overload
    def leqcons(self, n: Literal[False] = False) -> list[C]:
        """Return inequality rows by default."""
        ...

    @overload
    def leqcons(self, n: Literal[True]) -> list[int]:
        """Return assigned inequality row numbers when requested."""
        ...

    @overload
    def leqcons(self, n: bool) -> list[int] | list[C]:
        """Support a dynamically selected representation."""
        ...

    def leqcons(self, n: bool = False) -> list[int] | list[C]:
        """Return inequality rows or their assigned program row numbers."""
        if n:
            return [
                cast(int, x.n) for x in self.constraints if x.leq and not x.nn
            ]
        return [x for x in self.constraints if x.leq and not x.nn]

    @overload
    def cons(self, n: Literal[False] = False) -> list[C]:
        """Return constraint objects when row numbers are not requested."""
        ...

    @overload
    def cons(self, n: Literal[True]) -> list[int]:
        """Return solver row numbers when explicitly requested."""
        ...

    @overload
    def cons(self, n: bool) -> list[int] | list[C]:
        """Support callers selecting the representation dynamically."""
        ...

    def cons(self, n: bool = False) -> list[int] | list[C]:
        """
        Return inequality, equality, then non-negativity rows, or their IDs.
        """
        rows = [c for c in self.constraints if c.leq and not c.nn]
        rows.extend(c for c in self.constraints if not c.leq)
        rows.extend(c for c in self.constraints if c.nn)
        if n:
            return [cast(int, c.n) for c in rows]
        return rows

    def nnvars(self, n: bool = False) -> list[int | V]:
        """Return nonnegative variables or their assigned column numbers."""
        if n:
            return [cast(int, x.n) for x in self.variables if x.nn]
        return [x for x in self.variables if x.nn]

    def bnrvars(self, n: bool = False) -> list[int | V]:
        """Return binary variables or their assigned column numbers."""
        if n:
            return [cast(int, x.n) for x in self.variables if x.bnr]
        return [x for x in self.variables if x.bnr]

    def itgvars(self, n: bool = False) -> list[int | V]:
        """Return integer variables or their assigned column numbers."""
        if n:
            return [cast(int, x.n) for x in self.variables if x.itg]
        return [x for x in self.variables if x.itg]

    def nonbnritgvars(self, n: bool = False) -> list[int | V]:
        """Return nonbinary integers or their assigned column numbers."""
        if n:
            return [
                cast(int, x.n) for x in self.variables if x.itg and not x.bnr
            ]
        return [x for x in self.variables if x.itg and not x.bnr]

    def cntbnrvars(self, n: bool = False) -> list[int | V]:
        """Return continuous/binary variables or assigned column numbers."""
        if n:
            return [
                cast(int, x.n) for x in self.variables if not x.itg or x.bnr
            ]
        return [x for x in self.variables if not x.itg or x.bnr]

    def cntvars(self, n: bool = False) -> list[int | V]:
        """Return continuous variables or their assigned column numbers."""
        if n:
            return [
                cast(int, x.n)
                for x in self.variables
                if not x.bnr and not x.itg
            ]
        return [x for x in self.variables if not x.bnr and not x.itg]

    def renumber(self):
        """Assign solver row numbers while retaining native batches."""
        if native_registry.renumber(self.constraints):
            return
        for n, c in enumerate(self.cons()):
            c.n = n

    # --------------------------------------------------
    #               Matrices
    # --------------------------------------------------

    # Dense compatibility outputs intentionally allocate rows * columns.
    # Use A_sparse for a solver-sized sparse coefficient representation.

    def _compile_constraints(self):
        """Compile native rows without caching mutable model structure."""
        if not storage.NATIVE:
            return None
        return compile_program(self)

    @property
    def A_sparse(self):
        """Return detached float64 SciPy CSR coefficients in cons() row order.

        Sparse solver interchange uses floating-point coefficients. A and B
        retain the exact Python integer representation. Explicit zero entries
        may be retained; native compilation never allocates a dense matrix.
        """
        compiled = self._compile_constraints()
        if compiled is not None:
            return csr_matrix(
                compiled.parts(),
                shape=compiled.shape,
                dtype=float,
            )
        return self._legacy_sparse_constraints()

    def _legacy_sparse_constraints(self):
        """Compile compatibility rows without a dense intermediary."""
        data: list[float] = []
        indices: list[int] = []
        indptr = [0]
        for constraint in self.cons():
            row: dict[int, float] = {}
            for column, value in zip(constraint.P, constraint.A):
                # Compiled scalar rows contain concrete IDs and coefficients.
                column_id = cast(int, column)
                coefficient = cast(float, value)
                row[column_id] = row.get(column_id, 0) + coefficient
            indices.extend(row)
            data.extend(row.values())
            indptr.append(len(data))
        return csr_matrix(
            (data, indices, indptr),
            shape=(len(indptr) - 1, len(self.variables)),
            dtype=float,
        )

    @property
    def B(self) -> list[float]:
        """Export RHS bounds, retaining native batches when available."""
        compiled = self._compile_constraints()
        if compiled is not None:
            return compiled.rhs()
        return [cast(float, c.B) for c in self.cons()]

    @property
    def A(self) -> list[list[float]]:
        """Export dense coefficients, accumulating registered column IDs."""
        compiled = self._compile_constraints()
        if compiled is not None:
            return compiled.dense()
        constraints = self.cons()
        _A = []
        for _ in constraints:
            row: list[float] = [0] * len(self.variables)
            _A.append(row)

        for n, c in enumerate(constraints):
            for x, a in zip(cast("list[int]", c.P), cast("list[Number]", c.A)):
                _A[n][x] += a  # Accumulate repeated variable terms.
        return _A

    @property
    def F(self) -> list[list[float]]:
        """Export RHS theta coefficients in their independent column space."""
        compiled = (
            compile_program(self, theta=True) if storage.NATIVE else None
        )
        if compiled is not None:
            return compiled.dense()
        constraints = self.cons()
        _F = []
        for _ in constraints:
            row: list[float] = [0] * len(self.thetas)
            _F.append(row)

        for n, c in enumerate(constraints):
            for z, f in zip(c.Z, c.F):
                _F[n][z] += f
        return _F

    @property
    def C(self) -> list[float]:
        r"""
        Transpose of the Vector of Objective Coefficients
        :math:`C^{T}`
        """
        objective = self.active_objective
        if objective is None:
            return []
        coefficients: list[float] = [0] * len(self.variables)
        for column, coefficient in objective.matrix.items():
            coefficients[column] = coefficient
        return coefficients

    @property
    def P(self) -> list[list[int]]:
        r"""
        Registered column ordinals of variables :math:`v \in \mathcal{V}`.

        .. admonition:: Example

            The following constraints:

            .. math::

                5 \cdot \mathbf{v}_2 - 3 \cdot \mathbf{v}_3 + 15.2 \leq 0

                \mathbf{v}_0 = 1

                -4 \cdot \mathbf{v}_3 + \frac{\mathbf{v}_1}{13} = 0

            Correspond to:

            .. math::

                P = \begin{bmatrix}
                    2 & 3 \\
                    0 & \\
                    3 & 1
                    \end{bmatrix}
        """
        return [cast("list[int]", c.P) for c in self.cons()]

    @property
    def Z(self) -> list[list[int]]:
        r"""
        Ordinals of parametric variables :math:`\theta \in \Theta`

        .. admonition:: Example

            The following constraints:

            .. math::

                \mathbf{v}_1 - 2 \cdot \theta_1 + 21 \leq 0

                \mathbf{v}_0 - 7.23 \cdot \theta_0 = 0

                \theta_1  - 2 \cdot \mathbf{v}_0 - 31.56

            Corresponds to:

            .. math::

                Z = \begin{bmatrix}
                    1 \\
                    0 \\
                    1
                    \end{bmatrix}
        """
        return [c.Z for c in self.cons()]

    @property
    def G(self) -> list[list[float]]:
        r"""
        Coefficient matrix of inequality (leq) constraints

        .. admonition:: Example

            The following constraints:

            .. math::

                5 \cdot \mathbf{v}_2 - 3 \cdot \mathbf{v}_3 = 0

                -4 \cdot \mathbf{v}_3 + \frac{\mathbf{v}_1}{13} + 0.55 \leq 0

                3.73 \cdot \mathbf{v}_0 - 2 \cdot \theta_1 + 21 \leq 0

        """
        _G: list[list[float]] = [
            [0] * len(self.variables) for _ in range(len(self.leqcons()))
        ]

        for n, c in enumerate(self.leqcons()):
            for x, a in zip(
                cast("list[int | None]", c.P), cast("list[Number]", c.A)
            ):
                if x is not None:
                    _G[n][x] += a  # Accumulate repeated variable terms.

        return _G

    @property
    def H(self) -> list[list[float]]:
        """
        Coefficient matrix of equality constraints

        h = 0
        """
        _H: list[list[float]] = [
            [0] * len(self.variables) for _ in range(len(self.eqcons()))
        ]
        for n, c in enumerate(self.eqcons()):
            for x, a in zip(
                cast("list[int | None]", c.P), cast("list[Number]", c.A)
            ):
                if x is not None:
                    _H[n][x] += a  # Accumulate repeated variable terms.
        return _H

    @property
    def NN(self) -> list[list[float]]:
        """One bound row per non-negative variable, in declaration order."""
        _NN = []
        for column, variable in enumerate(self.variables):
            if variable.nn:
                row = [0.0] * len(self.variables)
                row[column] = -1.0
                _NN.append(row)
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
        # Float coefficients are written into the integer-zero buffers below.
        CrA_UB: list[list[float]] = [
            [0] * len(self.thetas) for _ in range(len(self.thetas))
        ]
        CrA_LB: list[list[float]] = [
            [0] * len(self.thetas) for _ in range(len(self.thetas))
        ]

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
        """Return critical-region bounds validated at theta registration."""
        CrB_ = []
        for t in self.thetas:
            CrB_.append(cast(Number, t.ub))
            CrB_.append(-cast(Number, t.lb))

        return CrB_

    def make_A_df(self, longname: bool = False) -> DataFrame:
        """
        Create a DataFrame from the A matrix.

        :param longname: Whether to use long names for variables. Defaults to
            False.
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

        :param longname: Whether to use long names for variables. Defaults to
            False.
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

        :param longname: Whether to use long names for variables. Defaults to
            False.
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

        :param longname: Use long variable names. Defaults to False.
        :type longname: bool

        :return: A DataFrame with the A matrix, B vector, and C vector.
        :rtype: DataFrame
        """

        if longname:
            index = ["Minimize"] + [c.longname for c in self.cons()]
            columns = [v.longname for v in self.variables] + ["RHS"]
        else:
            index = ["Minimize"] + [c.name for c in self.cons()]
            columns = [v.name for v in self.variables] + ["RHS"]
        data = []
        for n, d in enumerate(self.A):
            d.append(self.B[n])
            data.append(d)

        data = [[*self.C, 0], *data]

        return DataFrame(data, columns=columns, index=index)

    def make_CrA_df(self, longname: bool = False) -> DataFrame:
        """Pair each theta label with its two critical-region matrix rows."""

        if longname:
            columns = [t.longname for t in self.thetas]
            index = [name for t in self.thetas for name in [t.longname] * 2]
        else:
            columns = [t.name for t in self.thetas]
            index = [name for t in self.thetas for name in [t.name] * 2]

        return DataFrame(self.CrA, columns=columns, index=index)

    def make_CrB_df(self, longname: bool = False) -> DataFrame:
        """Repeat theta labels consecutively for critical-region RHS rows."""

        if longname:
            index = [name for t in self.thetas for name in [t.longname] * 2]
        else:
            index = [name for t in self.thetas for name in [t.name] * 2]

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
    @staticmethod
    def _write_mps_rows(stream, constraints, objective):
        """Declare the active objective and each exported constraint row."""
        stream.write("ROWS\n")
        objective_row = objective.mps() if objective is not None else "OBJ"
        stream.write(f" N   {objective_row}\n")
        for constraint in constraints:
            kind = "E" if constraint.eq else "L"
            stream.write(f" {kind}   {constraint.mps()}\n")

    @staticmethod
    def _write_mps_entry(stream, column, row, value):
        """Write one coefficient using the existing fixed-field spacing."""
        stream.write(f"    {column:<10}{row:<10}{value}\n")

    def _write_mps_variable(
        self,
        stream,
        variable,
        objective_row,
        coefficients,
        row_ids,
    ):
        """
        Write only declared rows and anchor unused columns with a zero entry.
        """
        column = variable.mps()
        written = False
        for constraint in variable.cons_by:
            if id(constraint) in row_ids:
                self._write_mps_entry(
                    stream,
                    column,
                    constraint.mps(),
                    constraint.matrix[variable.n],
                )
                written = True
        if variable.n in coefficients or not written:
            self._write_mps_entry(
                stream,
                column,
                objective_row,
                coefficients.get(variable.n, 0),
            )

    def _write_mps_columns(self, stream, objective, constraints, columns):
        """Export continuous/binary columns followed by marked integer columns.

        Build the objective map once: recomputing it per variable would make
        exporting a large scalar sum quadratic in the number of terms.
        """
        stream.write("COLUMNS\n")
        coefficients = objective.matrix if objective is not None else {}
        objective_row = objective.mps() if objective is not None else "OBJ"
        row_ids = {id(constraint) for constraint in constraints}
        column_ids = {id(variable) for variable in columns}
        regular, integer_columns = self._mps_column_groups()
        for variable in regular:
            if id(variable) in column_ids:
                self._write_mps_variable(
                    stream,
                    variable,
                    objective_row,
                    coefficients,
                    row_ids,
                )
        integers = [v for v in integer_columns if id(v) in column_ids]
        self._write_mps_integer_columns(
            stream,
            integers,
            objective_row,
            coefficients,
            row_ids,
        )

    def _write_mps_integer_columns(
        self,
        stream,
        integers,
        objective_row,
        coefficients,
        row_ids,
    ):
        """
        Mark a nonempty general-integer group without changing its column IDs.
        """
        if not integers:
            return
        stream.write("    MARK0000  'MARKER'                 'INTORG'\n")
        for variable in integers:
            self._write_mps_variable(
                stream,
                variable,
                objective_row,
                coefficients,
                row_ids,
            )
        stream.write("    MARK0000  'MARKER'                 'INTEND'\n")

    def _write_mps_rhs(self, stream, constraints, objective):
        """
        Export RHS values, including the negated objective constant offset.
        """
        stream.write("RHS\n")
        if objective is not None and objective.constant:
            self._write_mps_entry(
                stream,
                "RHS1",
                objective.mps(),
                -objective.constant,
            )
        for constraint in constraints:
            self._write_mps_entry(
                stream,
                "RHS1",
                constraint.mps(),
                constraint.B,
            )

    def _write_mps_bounds(self, stream, columns):
        """
        Encode each domain directly in one bound vector, without symbolic ==.

        MPS defaults to a zero lower bound, so free columns require FR.
        Integer markers preserve integrality for free general integers.
        """
        stream.write("BOUNDS\n")
        for variable in columns:
            if variable.bnr:
                kind, value = "BV", ""
            elif not variable.nn:
                kind, value = "FR", ""
            else:
                kind, value = ("LI" if variable.itg else "LO"), "0"
            stream.write(f" {kind} BND1      {variable.mps():<10}{value}\n")

    @timer(logger, kind="generate-mps", with_return=False)
    def mps(self, name: str | None = None):
        """
        Export the active scalar objective, its offset, and constraint rows.
        """
        output_name = name or self.name
        snapshot = self._native_export()
        if snapshot is not None:
            self._write_native_mps(snapshot, output_name)
            return output_name
        self.renumber()
        constraints = [c for c in self.cons() if not c.redundant_bound]
        objective = self.active_objective
        _, columns = self._solution_columns()
        with open(f"{output_name}.mps", "w", encoding="utf-8") as stream:
            stream.write(f"NAME          {self.name.upper()}\n")
            self._write_mps_rows(stream, constraints, objective)
            self._write_mps_columns(stream, objective, constraints, columns)
            self._write_mps_rhs(stream, constraints, objective)
            self._write_mps_bounds(stream, columns)
            stream.write("ENDATA")
        return output_name

    def _native_export(self):
        """
        Build a transient sparse adapter only for supported native models.
        """
        return build_native_export(self) if storage.NATIVE else None

    def _write_native_mps(self, snapshot, name):
        """
        Retain the public MPS file side effect using exact sparse coefficients.
        """
        renumber_native_export(self)
        with open(f"{name}.mps", "w", encoding="utf-8") as stream:
            snapshot.write(stream, self.name)

    def lp(self):
        """LP File"""
        m = self.gurobi()
        m.write(f"{self.name}.lp")

    # --------------------------------------------------
    #               Optimize
    # --------------------------------------------------

    @timer(logger, kind="optimize", with_return=False)
    def opt(self, using: str = "gurobi"):
        """Determine the optimal solution to the program"""

        if using == "gurobi":
            m = self.gurobi()

            self.formulations[self.n_formulations] = m
            self.n_formulations += 1

            m.optimize()
            try:
                self._load_values(
                    ({v.VarName: v.X for v in m.getVars()}, m.ObjVal),
                )
                self.optimized = True
                self._birth_solution()

            except AttributeError:
                logger.warning("🛑 No solution found. Check the model 🛑")

                return False
            else:
                return self, using
        return None

    def _mps_column_groups(self) -> tuple[list[V], list[V]]:
        """
        Partition declarations in one pass, retaining order within each domain.
        """
        regular: list[V] = []
        integers: list[V] = []
        for variable in self.variables:
            group = integers if variable.itg and not variable.bnr else regular
            group.append(variable)
        return regular, integers

    def _solution_columns(self):
        """
        Return full and legacy referenced columns in deterministic MPS order.
        """
        regular, integers = self._mps_column_groups()
        columns = regular + integers
        objective = self.active_objective
        coefficients = objective.matrix if objective is not None else {}
        referenced = [v for v in columns if v.cons_by or v.n in coefficients]
        return columns, referenced

    def _normalize_solution_values(self, values):
        """
        Validate names/lengths before mutation; missing unused columns are
        None.

        Legacy sequences follow MPS order: continuous/binary, then integers.
        They may omit unused columns, as older Gana exports did. Without model
        metadata, positional imports require the original declarations/order.
        """
        columns, referenced = self._solution_columns()
        if not isinstance(values, Mapping):
            if len(values) == len(columns):
                selected = columns
            elif len(values) == len(referenced):
                selected = referenced
            else:
                message = "Solution length does not match exported columns"
                raise ValueError(message)
            values = {v.mps(): value for v, value in zip(selected, values)}
        unknown = values.keys() - {v.mps() for v in columns}
        missing = {v.mps() for v in referenced} - values.keys()
        if unknown or missing:
            message = (
                f"Invalid solution columns: unknown={unknown}, "
                f"missing={missing}"
            )
            raise ValueError(message)
        return [values.get(v.mps()) for v in self.variables]

    def _load_values(self, sol_and_obj):
        """
        Load (column values, objective); store variable history in declaration
        order.
        """
        values, objective_value = sol_and_obj
        snapshot = self._native_export()
        if snapshot is not None and load_native_results(
            self,
            snapshot,
            values,
            objective_value,
        ):
            return
        solution = self._normalize_solution_values(values)
        self.X[self.n_solutions] = solution
        for variable, value in zip(self.variables, solution):
            variable.X[self.n_solutions] = value
        for constraint in self.constraint_sets:
            constraint.function.solution(n_sol=self.n_solutions)
        if self.active_objective is not None:
            self.active_objective.X = objective_value

    def import_solution(self, name: str):
        """Import JSON/pickle containing (column values, objective value).

        Prefer values keyed by exported names (Vn, or Xn for binary variables).
        Legacy lists use MPS column order, with optional omission of unused
        columns. Positional files must match the original model declarations.

        Pickle files must come from a trusted source: loading them can execute
        Python code. Use JSON when exchanging solution data with other sources.

        :param name: file name, with extenstion
        :type name: str

        """
        ext = Path(name).suffix

        if ext == ".json":
            with open(name, "r") as f:
                sol_and_obj = json.load(f)

        elif ext == ".pkl":
            with open(name, "rb") as f:
                # Approved compatibility path for trusted files only.
                sol_and_obj = pickle.load(f)  # noqa: S301

        else:
            _error_message = "Unsupported file type. Use .json or .pkl"
            raise ValueError(_error_message)

        self._load_values(sol_and_obj)

        self.optimized = True
        self._birth_solution()

    @timer(logger, kind="solve-mpqp")
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
    ):
        """Solve the multiparametric program with the selected algorithm."""

        m = self.ppopt()
        self.formulations[self.n_formulations] = m
        self.n_formulations += 1

        # PPOPT 1.6.12 explicitly supports MPLPs in solve_mpqp's implementation
        # and docstring, but annotates only MPQP_Program. Keep that documented
        # callable contract without pretending the linear model is quadratic.
        solve_linear = cast(
            Callable[[MPLP_Program, mpqp_algorithm], MPSolution],
            solve_mpqp,
        )
        sol = solve_linear(m, getattr(mpqp_algorithm, using))
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
            # setattr(cr, mat, npround(getattr(cr, mat), decimals=round_off))
            #     A = cr.A.T
            #     # write the evaluation function
            #     f = sum(list(a) * t for a, t in zip(A, _p.t._)) + list(cr.b)

            #     setattr(_p, f"v_cr{n}", f)
            #     # this add the equations determining variable values
            #     # as a function of parametric variables
            #     # in a dictionary for each variable to hold them
            #     for _v, _f in zip(self.variables, f):
            #         _v.eval_funcs.setdefault(self.n_sol, {})[n] = _f

            self.solutions[self.n_solutions] = sol
            self.sol_types["mp"].append(self.n_solutions)
            self.n_solutions += 1

        return sol

    def eval(
        self,
        *theta_vals: float,
        n_sol: int = 0,
        roundoff: int = 4,
    ) -> dict[V, float]:
        """
        Evaluates the variable value as a function of parametric variables

        :param theta_vals: values of the parametric variables
        :type theta_vals: float
        :param n_sol: solution number, defaults to 0
        :type n_sol: int, optional
        :param roundoff: round off the evaluated value, defaults to 4
        :type roundoff: int, optional

        :returns: evaluated values keyed by their model variables
        :rtype: dict[V, float]

        :raises ValueError: if number of theta values provided does not match
            number of thetas in the problem
        """
        if len(theta_vals) != self.n_thetas:
            _error_message = (
                f"Problem has {self.n_thetas} thetas, "
                f"provided {len(theta_vals)} values"
            )
            raise ValueError(_error_message)

        _theta_vals = nparray([[v] for v in theta_vals])
        # Evaluation requires a multiparametric solution; ordinary solution
        # records retain their existing missing-evaluate failure.
        evaluated = cast(MPSolution, self.solutions[n_sol]).evaluate(
            _theta_vals
        )
        if evaluated is None:
            # Preserve the previous TypeError while explaining the missing
            # region before any evaluation history can be updated.
            message = "No solution exists for the supplied theta values"
            raise TypeError(message)
        sol = [round(float(val[0]), roundoff) for val in evaluated]

        self.evaluation.setdefault(n_sol, {})
        self.n_evaluation.setdefault(n_sol, 0)

        self.evaluation[n_sol][theta_vals] = sol

        self.n_evaluation[n_sol] += 1

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

    def output(self, n_sol: int = 0, compare=False):
        """Display the selected solution's objective and variable values."""

        if not self.optimized:
            return r"Use .opt() to generate solution"

        display(Markdown(rf"# Solution for {self.name}"))

        display(Markdown("<br><br>"))
        display(Markdown(r"## Objective"))

        self.objectives[n_sol].output()

        display(Markdown("<br><br>"))
        display(Markdown(r"## Variables"))

        for v in self.variable_sets:
            v.output(n_sol=n_sol, compare=compare)
        return None

    @timer(logger, kind="generate-solution", with_return=False)
    def _birth_solution(self):
        """Makes a solution object for the program"""

        _solution = Solution(self.name + "_solution_" + str(self.n_solutions))
        _solution.update(self.variables, n_sol=self.n_solutions)

        self.solutions[self.n_solutions] = _solution
        self.sol_types["MIP"].append(self.n_solutions)
        self.n_solutions += 1

        return self

    def _display_indices(self) -> list[I]:
        """Return nonempty index sets, excluding scalar self-indices."""
        return [
            index
            for index in (getattr(self, "index_sets", None) or ())
            if len(index) != 0 and index.case != ICase.SELF
        ]

    @staticmethod
    def _group_display_categories[Item: _DisplayItem](
        items: Sequence[Item],
    ) -> dict[str, list[Item]]:
        """Group objects without changing order within each category."""
        grouped: dict[str, list[Item]] = {}
        for item in items:
            grouped.setdefault(item.category, []).append(item)
        return grouped

    @staticmethod
    def _display_category_keys(
        grouped: Mapping[str, Sequence[_DisplayItem]],
        category: str | None,
    ) -> list[str]:
        """Select a known category; retain the historical fallback to all."""
        if category and category in grouped:
            return [category]
        return sorted(grouped)

    def _category_display_sections(
        self,
        descriptive: bool,
        category: str | None,
        *,
        notebook: bool,
    ) -> list[_DisplaySection]:
        """Build ordered category sections and retain notebook cache behavior.

        A category may exist only for constraints or only for functions.
        Apply selection independently to each group, including its fallback.
        LaTeX output retains its existing plural titles even for set views.
        """
        constraints = self.cons() if descriptive else self.constraint_sets
        functions = self.functions if descriptive else self.function_sets
        categories = self._group_display_categories(constraints)
        fcategories = self._group_display_categories(functions)
        if notebook:
            self.categories = categories
            self.fcategories = fcategories
        suffix = " Sets" if notebook and not descriptive else "s"
        sections: list[_DisplaySection] = []
        for kind, grouped in (
            ("Constraint", categories),
            ("Function", fcategories),
        ):
            for name in self._display_category_keys(grouped, category):
                sections.append((2, f"{name} {kind}{suffix}", grouped[name]))
        return sections

    def _plain_display_sections(
        self,
        descriptive: bool,
        nncons: bool,
    ) -> list[_DisplaySection]:
        """Select standard sections in their established display order.

        Only descriptive, non-categorical views use the nonnegativity flag.
        Section levels describe LaTeX/Markdown output; notebook sections keep
        their existing uniform level-two headings.
        """
        # Default selectors return rows; n=True selects assigned integer IDs.
        if descriptive:
            return [
                (
                    2,
                    "Inequality Constraints",
                    self.leqcons(),
                ),
                (
                    2,
                    "Equality Constraints",
                    self.eqcons(),
                ),
                (
                    2,
                    "Non-Negative Constraints",
                    cast("Sequence[_DisplayItem]", self.nncons())
                    if nncons
                    else [],
                ),
                (1, "Functions", getattr(self, "functions", None) or ()),
            ]
        return [
            (
                2,
                "Inequality Constraint Sets",
                getattr(self, "leqcons_sets", None) or (),
            ),
            (
                2,
                "Equality Constraint Sets",
                getattr(self, "eqcons_sets", None) or (),
            ),
            (1, "Functions", getattr(self, "function_sets", None) or ()),
        ]

    @staticmethod
    def _latex_heading(level: int, text: str, as_document: bool) -> str:
        """Render a section heading using the requested output syntax."""
        return (
            rf"\{'sub' * (level - 1)}section*{{{text}}}"
            if as_document
            else f"{'#' * (level + 1)} {text}"
        )

    def _latex_intro(self, as_document: bool) -> list[str]:
        """Render nonempty index and objective sections before constraints."""
        lines = []
        indices = [
            index.latex(descriptive=True) for index in self._display_indices()
        ]
        if indices:
            lines.append(self._latex_heading(1, "Index Sets", as_document))
            lines.extend(indices)
        objectives = [
            obj.latex() for obj in (getattr(self, "objectives", None) or ())
        ]
        if objectives:
            lines.append(self._latex_heading(1, "Objective", as_document))
            lines.extend(objectives)
        return lines

    def latex(
        self,
        descriptive: bool = False,
        categorical: bool = False,
        category: str | None = None,
        as_document: bool = False,
    ) -> str:
        r"""Render the program with Markdown or LaTeX document headings.

        A nonempty category enables categorical output. Unknown categories
        preserve the existing fallback to all categories for each object kind.
        """
        lines = [rf"\textbf{{Mathematical Program for }} {self}"]
        lines.extend(self._latex_intro(as_document))
        lines.append(self._latex_heading(1, "Subject to", as_document))
        if categorical or category:
            sections = self._category_display_sections(
                descriptive,
                category,
                notebook=False,
            )
        else:
            sections = self._plain_display_sections(descriptive, nncons=True)
        for level, title, items in sections:
            if items:
                lines.append(self._latex_heading(level, title, as_document))
                lines.extend(f"${item.latex()}$" for item in items)
        body = "\n\n".join(lines)
        if as_document:
            return rf"""
    \documentclass{{article}}
    \usepackage{{amsmath, amssymb}}
    \usepackage[margin=1in]{{geometry}}
    \begin{{document}}
    {body}
    \end{{document}}
    """.strip()
        return body

    @staticmethod
    def _show_section(
        title: str,
        items: Sequence[I | O | _DisplayItem] | None,
    ) -> None:
        """Emit a nonempty notebook section with its existing leading break."""
        if items:
            display(Markdown("<br><br>"))
            display(Markdown(rf"## {title}"))
            for item in items:
                item.show()

    def show(
        self,
        descriptive: bool = False,
        nncons: bool = False,
        categorical: bool = False,
        category: str | None = None,
    ):
        """Display the program, preserving headings and category caches.

        Nonnegativity rows are optional only in the plain descriptive view.
        Categorical views keep their existing constraint selection behavior.
        """
        display(Markdown(rf"# Mathematical Program for {self}"))
        self._show_section("Index Sets", self._display_indices())
        self._show_section("Objective", getattr(self, "objectives", None))
        display(Markdown("<br><br>"))
        display(Markdown(r"## s.t."))
        if categorical or category:
            sections = self._category_display_sections(
                descriptive,
                category,
                notebook=True,
            )
            for _, title, items in sections:
                display(Markdown(rf"### {title}"))
                for item in items:
                    item.show()
        else:
            for _, title, items in self._plain_display_sections(
                descriptive,
                nncons,
            ):
                self._show_section(title, items)

    def draw(self, variable: V | None = None, n_sol: int = 0):
        """Plot a MIP variable or a multiparametric region.

        The region plot needs no variable. MIP callers must supply one;
        preserve the existing failure when it is omitted on that path.
        """
        if n_sol in self.sol_types["MIP"]:
            cast(Solution, self.solutions[n_sol]).draw(cast(V, variable))
        elif n_sol in self.sol_types["mp"]:
            parametric_plot(cast(MPSolution, self.solutions[n_sol]))
        else:
            _error_message = f"Solution {n_sol} not found"
            raise ValueError(_error_message)

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

    def __init_subclass__(cls):
        """Install program representation and hashing on each subclass."""
        for name, method in (
            ("__repr__", Prg.__repr__),
            ("__hash__", Prg.__hash__),
        ):
            setattr(cls, name, method)

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
        """Convert constraints and the active affine objective to ppopt."""

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
        objective = self.active_objective
        constant = objective.constant if objective is not None else 0

        _mplp = MPLP_Program(
            A=nparray(_A + _NN),
            b=nparray([[i] for i in _B] + [[0]] * len(_NN)),
            c=nparray([[i] for i in _C]),
            c_c=nparray([[constant]]),
            A_t=nparray(_CrA),
            b_t=nparray([[i] for i in _CrB]),
            F=nparray(_F + [[0] * self.n_thetas] * len(_NN)),
            H=npzeros((self.n_variables, self.n_thetas)),
            equality_indices=[n for n, c in enumerate(self.cons()) if c.eq],
        )
        self.formulations[self.n_formulations] = _mplp
        self.n_formulations += 1

        return _mplp

    @timer(logger, kind="generate-gurobi")
    def gurobi(self) -> GPModel:
        """
        Build native models through bulk CSR APIs, retaining the MPS artifact.
        """
        snapshot = self._native_export()
        if snapshot is not None:
            self._write_native_mps(snapshot, self.name)
            return snapshot.gurobi(self.name, GPModel, csr_matrix)
        self.mps()
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
    # 'pyomo is an optional dependency, pip install gana[all] to get optional
    # dependencies'
    #     )
