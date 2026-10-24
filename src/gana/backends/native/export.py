"""Transient solver snapshots over native CSR batches and owner metadata.

Snapshots are rebuilt for each public operation. They contain no scalar V/F/C
objects and never become a program-wide cache. Unsupported or exposed legacy
rows continue through the existing adapters.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from numpy import array

from ...storage.symbols import SymbolRegistry
from .constraints import _negative_variable, _ordered_sets, compile_program
from .theta import has_thetas


def owner_members(registry):
    """Traverse accepted registration spans without constructing V wrappers."""
    previous = 0
    for (root, start), end in zip(registry.spans, registry.ends):
        owner = root.__dict__["_symbol_storage"].owner
        for position in range(start, start + end - previous):
            yield owner, position
        previous = end


def _supported(program):
    """Require native columns and an untouched native scalar objective."""
    # Parametric programs use the established solver adapters. Projecting A
    # alone here would silently discard their independent RHS theta matrix.
    if any(
        "_native_owners" in item.function.__dict__
        and has_thetas(item.function)
        for item in program.constraint_sets
    ):
        return False
    if not isinstance(program.variables, SymbolRegistry):
        return False
    if any(
        "_symbol_storage" not in root.__dict__
        for root, _ in program.variables.spans
    ):
        return False
    objective = program.active_objective
    if objective is None:
        return True
    return (
        "_native_owners" in objective.__dict__
        and objective.function._is_lazy()
    )


def _domains(registry):
    """Honor captured growth metadata and any explicit scalar domain edits."""
    kinds, nonnegative = [], []
    for owner, position in owner_members(registry):
        state = owner.states.get(position, owner.template(position)["args"])
        kind = "B" if state["bnr"] else ("I" if state["itg"] else "C")
        kinds.append(kind)
        nonnegative.append(state["nn"])
    return kinds, nonnegative


def _rows(program, indices, indptr, nonnegative):
    """Retain row IDs/order and omit only established redundant bound rows."""
    kept, senses = [], []
    start = 0
    for constraint in _ordered_sets(program.constraint_sets):
        negative = constraint.leq and _negative_variable(constraint.function)
        for row in range(start, start + len(constraint)):
            begin, end = indptr[row], indptr[row + 1]
            columns = indices[begin:end]
            redundant = negative and all(
                nonnegative[column] for column in columns
            )
            if not redundant:
                kept.append(row)
                senses.append("<" if constraint.leq else "=")
        start += len(constraint)
    return kept, senses


def renumber(program):
    """Commit MPS row numbering only when export is actually requested."""
    start = 0
    for constraint in _ordered_sets(program.constraint_sets):
        constraint._native_number_start = start
        start += len(constraint)


def build(program):
    """
    Capture one consistent sparse representation or request compatibility.
    """
    if not _supported(program):
        return None
    compiled = compile_program(program)
    if compiled is None:
        return None
    objective = program.active_objective
    kinds, nonnegative = _domains(program.variables)
    data, indices, indptr = compiled.parts()
    kept, senses = _rows(program, indices, indptr, nonnegative)
    coefficients = objective.matrix if objective is not None else {}
    return ExportSnapshot(
        data,
        indices,
        indptr,
        compiled.rhs(),
        kept,
        senses,
        kinds,
        nonnegative,
        coefficients,
        objective.mps() if objective is not None else "OBJ",
        objective.constant if objective is not None else 0,
    )


@dataclass
class ExportSnapshot:
    """Detached coefficients and domain arrays in stable declaration order."""

    data: list
    indices: list[int]
    indptr: list[int]
    rhs: list
    rows: list[int]
    senses: list[str]
    kinds: list[str]
    nonnegative: list[bool]
    objective: dict
    objective_name: str
    constant: int | float

    @property
    def referenced(self):
        """
        Include cancellation and redundant-row references, as cons_by did.
        """
        return set(self.indices) | self.objective.keys()

    @property
    def ordered(self):
        """Place general integers last while retaining original global IDs."""
        regular = [n for n, kind in enumerate(self.kinds) if kind != "I"]
        return regular + [
            n for n, kind in enumerate(self.kinds) if kind == "I"
        ]

    @property
    def selected(self):
        """Keep the historical omission of completely unused declarations."""
        referenced = self.referenced
        return [n for n in self.ordered if n in referenced]

    def column_name(self, number):
        """Keep binary Xn and continuous/general-integer Vn identifiers."""
        return ("X" if self.kinds[number] == "B" else "V") + str(number)

    def normalize(self, values):
        """
        Validate named or legacy positional values before any history changes.
        """
        if not isinstance(values, Mapping):
            columns = (
                self.ordered
                if len(values) == len(self.kinds)
                else self.selected
            )
            if len(values) != len(columns):
                message = "Solution length does not match exported columns"
                raise ValueError(message)
            values = {
                self.column_name(n): value for n, value in zip(columns, values)
            }
        names = [self.column_name(n) for n in range(len(self.kinds))]
        unknown = values.keys() - set(names)
        missing = {names[n] for n in self.referenced} - values.keys()
        if unknown or missing:
            message = (
                f"Invalid solution columns: unknown={unknown}, "
                f"missing={missing}"
            )
            raise ValueError(message)
        return [values.get(name) for name in names]

    def _columns(self):
        """
        Transpose exact coefficients for column-oriented MPS text in O(nnz).
        """
        columns: list[list[tuple[int, int | float]]] = [[] for _ in self.kinds]
        for row in self.rows:
            for position in range(self.indptr[row], self.indptr[row + 1]):
                columns[self.indices[position]].append(
                    (row, self.data[position]),
                )
        return columns

    @staticmethod
    def _entry(stream, column, row, value):
        """Preserve fixed-field spacing and exact Python numeric formatting."""
        stream.write(f"    {column:<10}{row:<10}{value}\n")

    def _write_column(self, stream, number, entries):
        """
        Anchor columns with only redundant rows using a zero objective term.
        """
        name = self.column_name(number)
        for row, coefficient in entries:
            self._entry(stream, name, f"C{row}", coefficient)
        if number in self.objective or not entries:
            self._entry(
                stream,
                name,
                self.objective_name,
                self.objective.get(number, 0),
            )

    def _write_columns(self, stream, selected):
        """
        Emit the integer marker once, leaving continuous/binary columns first.
        """
        stream.write("COLUMNS\n")
        columns, marked = self._columns(), False
        for number in selected:
            if self.kinds[number] == "I" and not marked:
                stream.write(
                    "    MARK0000  'MARKER'                 'INTORG'\n",
                )
                marked = True
            self._write_column(stream, number, columns[number])
        if marked:
            stream.write("    MARK0000  'MARKER'                 'INTEND'\n")

    def _write_bounds(self, stream, selected):
        """Preserve binary, free and nonnegative continuous/integer domains."""
        stream.write("BOUNDS\n")
        for number in selected:
            if self.kinds[number] == "B":
                kind, value = "BV", ""
            elif not self.nonnegative[number]:
                kind, value = "FR", ""
            else:
                kind, value = (
                    ("LI" if self.kinds[number] == "I" else "LO"),
                    "0",
                )
            stream.write(
                f" {kind} BND1      {self.column_name(number):<10}{value}\n",
            )

    def write(self, stream, name):
        """
        Serialize native sparse data without consulting scalar bookkeeping.
        """
        stream.write(
            f"NAME          {name.upper()}\nROWS\n"
            f" N   {self.objective_name}\n",
        )
        for row, sense in zip(self.rows, self.senses):
            stream.write(f" {'E' if sense == '=' else 'L'}   C{row}\n")
        selected = self.selected
        self._write_columns(stream, selected)
        stream.write("RHS\n")
        if self.constant:
            self._entry(stream, "RHS1", self.objective_name, -self.constant)
        for row in self.rows:
            self._entry(stream, "RHS1", f"C{row}", self.rhs[row])
        self._write_bounds(stream, selected)
        stream.write("ENDATA")

    def _add_variables(self, model, selected):
        """
        Build solver columns in MPS order with explicit domains and objective.
        """
        return model.addMVar(
            len(selected),
            lb=[
                0
                if self.nonnegative[n] or self.kinds[n] == "B"
                else -float("inf")
                for n in selected
            ],
            ub=[1 if self.kinds[n] == "B" else float("inf") for n in selected],
            obj=[self.objective.get(n, 0) for n in selected],
            vtype=array([self.kinds[n] for n in selected]),
            name=array([self.column_name(n) for n in selected]),
        )

    def gurobi(self, name, model_factory, sparse_factory):
        """
        Use Gurobi's bulk sparse API; release its model on construction errors.
        """
        model = model_factory(name.upper())
        try:
            selected = self.selected
            variables = self._add_variables(model, selected)
            matrix = sparse_factory(
                (self.data, self.indices, self.indptr),
                shape=(len(self.rhs), len(self.kinds)),
                dtype=float,
            )
            if self.rows:
                model.addMConstr(
                    matrix[self.rows][:, selected],
                    variables,
                    array(self.senses),
                    array([self.rhs[n] for n in self.rows]),
                    name=array([f"C{n}" for n in self.rows]),
                )
            model.ObjCon = self.constant
            model.update()
        except Exception:
            model.dispose()
            raise
        else:
            return model
