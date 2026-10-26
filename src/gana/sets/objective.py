"""Objective Function"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, cast

from IPython.display import Math, display

from gana.types import Number

if TYPE_CHECKING:
    from ..backends.native.algebra import NativeRows
    from .function import F
    from .variable import V


class O:
    """
    Objective Function

    :param function: function to minimize
    :type function: F | V
    """

    # region Construction and ownership

    def __init__(self, function: F | V):
        """Capture one scalar row while retaining the expression for display.

        Indexed objectives must be reduced explicitly. A variable's scalar
        member still exposes a nested A matrix, whereas an F member exposes
        its coefficient vector directly. Constants use F's negated-RHS sign.
        """
        if len(function) != 1:
            message = (
                "An objective must be scalar; explicitly reduce indexed "
                "expressions with sigma or select one scalar member."
            )
            raise ValueError(message)
        function, initialized = self._initialize_native(function)
        if initialized:
            return
        if getattr(function, "rhs_thetas", ()):
            message = "Theta-dependent objectives are not supported"
            raise ValueError(message)
        # A valid scalar objective has a populated row; preserve the original
        # attribute errors for incomplete expressions rather than filtering.
        self.function = (
            cast("F | V", function[0])
            if all(v.parent is None for v in function.variables)
            else function
        )
        row = cast("F | V", function[0])
        coefficients = row.A
        # The preceding shape check flattens V's single row; F is already flat.
        self.C = cast(
            "list[Number]",
            coefficients[0]
            if coefficients and isinstance(coefficients[0], list)
            else coefficients,
        )
        self.constant = -(getattr(row, "B", 0) or 0)
        self._ = self.function

        # The index is taken from the function
        self.index = self.function.index
        # so are the variables

        self.variables = row.variables
        # the name, always minimization in gana
        self.name = rf"min({self.function})"
        # whats contained in the set

        # value obtained after optimization
        self.X: float | None = None

        # number in the program
        self.n: int | None = None

        # name given by user in program
        self.pname: str | None = None

    def _initialize_native(self, function):
        """Reject theta dependence before capturing a native scalar objective.

        An exposed selection must use its shared mutable compatibility rows.
        Return those rows for ordinary initialization when native capture is
        unavailable; leave the scalar-size check with the public constructor.
        """
        if "_native_batch" not in function.__dict__:
            return function, False
        native = cast("NativeRows", function)
        if import_module("gana.backends.native.theta").has_thetas(native):
            message = "Theta-dependent objectives are not supported"
            raise ValueError(message)
        if native._is_lazy():
            import_module("gana.backends.native.algebra").initialize_objective(
                self,
                function,
            )
            return function, True
        return native._materialize(), False

    def update_variables(self):
        """
        Register an objective once per variable identity for solver export.
        """
        if "_native_owners" in self.__dict__:
            import_module("gana.backends.native.algebra").objective_links(self)
            return
        # Repeated terms share a column and must emit one accumulated value.
        for v in {id(v): v for v in self.variables}.values():
            v.min_by.append(self)

    def unregister_variables(self):
        """
        Remove inactive export registrations without discarding solve history.
        """
        if "_native_owners" in self.__dict__:
            import_module("gana.backends.native.algebra").objective_links(
                self,
                remove=True,
            )
            return
        for v in {id(v): v for v in self.variables}.values():
            v.min_by[:] = [
                objective for objective in v.min_by if objective is not self
            ]

    # endregion

    # region Matrix representation

    def _native_matrix_current(self):
        """Selections must honor scalar rows shared with an exposed source."""
        if "_native_owners" not in self.__dict__:
            return False
        if "_native_selection_root" in self.function.__dict__:
            return cast("NativeRows", self.function)._is_lazy()
        return True

    @property
    def P(self):
        """Variable positions"""
        if self._native_matrix_current():
            return self._native_batch.columns(0)
        return [v.n for v in self.variables]

    @property
    def matrix(self) -> dict:
        """
        Map scalar columns to accumulated coefficients, including repeats.
        """
        if self._native_matrix_current():
            try:
                return dict(self._native_batch.matrix(0))
            except OverflowError:
                pass  # Preserve unbounded Python column accumulation.
        # Column IDs may still be unset before registration assigns numbers.
        coefficients: dict[int | None, Number] = {}
        for variable, coefficient in zip(self.variables, self.C):
            coefficients[variable.n] = (
                coefficients.get(variable.n, 0) + coefficient
            )
        return coefficients

    def __getattr__(self, name):
        """
        Materialize only the native objective attributes explicitly requested.
        """
        if "_native_owners" not in self.__dict__:
            raise AttributeError(name)
        if name == "_native_batch":
            # Copy/pickle can restore O before its function through owner
            # links.
            # Resolve only on use, once the complete graph has received state.
            batch = cast("NativeRows", self.function)._native_batch
            self.__dict__[name] = batch
            return batch
        if name == "C":
            if "_native_selection_root" in self.function.__dict__:
                # The public coefficient list aliases the selected scalar row.
                return cast("F", self.function[0]).A
            return self._native_batch.coefficients(0)
        if name == "variables":
            return cast("F", self.function[0]).variables
        if name == "index":
            return self.function.index
        if name == "name":
            return rf"min({self.function})"
        raise AttributeError(name)

    def __getstate__(self):
        """Serialize native rows through their owning expression only once."""
        return {
            key: value
            for key, value in self.__dict__.items()
            if key != "_native_batch"
        }

    def __setstate__(self, state):
        """
        Restore references without reading a partially reconstructed function.

        Owner membership creates cycles, so the function may receive its native
        batch after this objective. __getattr__ resolves that shared batch on
        first use; it never creates a second copy of the coefficient storage.
        """
        self.__dict__.update(state)

    # endregion

    # region Solution and output

    def output(self, asfloat: bool = False):
        """Solution"""
        if asfloat:
            return self.X

        display(Math(self.latex() + r"=" + rf"{self.X}"))
        return None

    # endregion

    # region Display and export

    def latex(self):
        """Latex representation"""
        return rf"min \hspace{{0.2cm}} {self.function.latex()}"

    def show(self):
        """Pretty Print"""
        display(Math(self.latex()))

    def mps(self):
        """Name in MPS file"""
        return f"O{self.n}"

    def __str__(self):
        return rf"{self.name}"

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    # endregion
