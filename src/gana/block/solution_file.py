"""Version 1 of Gana's deterministic result file."""

import json
from collections.abc import Iterable, Mapping
from hashlib import sha256
from math import isfinite
from pathlib import Path
from re import fullmatch
from sys import float_info
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Literal, TypedDict

from gana.types import Number

if TYPE_CHECKING:
    from ..backends.native.export import ExportSnapshot


class SolutionRecord(TypedDict):
    """Store the fields needed to inspect or attach a deterministic result."""

    format_version: Literal[1]
    values: dict[str, Number]
    objective_value: Number
    objective_sense: Literal["min"]
    status: Literal["optimal", "incumbent"]
    formulation_fingerprint: str


def _solver_number(value: Number) -> str:
    """Canonicalize solver doubles, including either sign of zero."""
    return (float(value) or 0.0).hex()


def _terms(coefficients: Mapping[int, Number]) -> list[tuple[int, str]]:
    """Encode sparse terms independently of dictionary insertion order."""
    return [
        (column, _solver_number(value))
        for column, value in sorted(coefficients.items())
        if value != 0
    ]


def formulation_fingerprint(
    columns: Iterable[tuple[str, str, bool]],
    objective: Mapping[int, Number],
    constant: Number,
    rows: Iterable[tuple[str, Number, Mapping[int, Number]]],
) -> str:
    """Hash the exported columns, minimization objective, and sparse rows."""
    digest = sha256(b"gana-deterministic-formulation-v1\n")
    digest.update(json.dumps(list(columns)).encode())
    digest.update(b"\n")
    digest.update(
        json.dumps((_solver_number(constant), _terms(objective))).encode()
    )
    for sense, rhs, coefficients in rows:
        digest.update(b"\n")
        digest.update(
            json.dumps(
                (sense, _solver_number(rhs), _terms(coefficients))
            ).encode(),
        )
    return f"sha256:{digest.hexdigest()}"


def fingerprint_snapshot(snapshot: "ExportSnapshot") -> str:
    """Read columns and rows from a native export snapshot."""
    columns = (
        (
            snapshot.column_name(n),
            snapshot.kinds[n],
            snapshot.nonnegative[n] or snapshot.kinds[n] == "B",
        )
        for n in snapshot.selected
    )
    rows = (
        (
            sense,
            snapshot.rhs[row],
            {
                snapshot.indices[i]: snapshot.data[i]
                for i in range(snapshot.indptr[row], snapshot.indptr[row + 1])
            },
        )
        for row, sense in zip(snapshot.rows, snapshot.senses)
    )
    return formulation_fingerprint(
        columns,
        snapshot.objective,
        snapshot.constant,
        rows,
    )


def _finite_number(value: object) -> bool:
    """Accept JSON numbers that can be represented as finite solver values."""
    if type(value) is int:
        return abs(value) <= float_info.max
    return type(value) is float and isfinite(value)


def _validate_values(values: object, objective: object) -> None:
    """Validate result numbers before any values are loaded into a program."""
    if not isinstance(values, dict) or not all(
        _finite_number(value) for value in values.values()
    ):
        message = "Solution values must be an object of finite column values"
        raise ValueError(message)
    if not _finite_number(objective):
        message = "Solution objective value must be a finite number"
        raise ValueError(message)


def validate_record(data: dict) -> SolutionRecord:
    """Validate the version, result metadata, and values from a JSON object."""
    version = data.get("format_version")
    if type(version) is not int or version != 1:
        message = f"Unsupported solution format version: {version!r}"
        raise ValueError(message)
    if data.get("objective_sense") != "min":
        message = "Expected Gana's minimization objective sense"
        raise ValueError(message)
    if data.get("status") not in ("optimal", "incumbent"):
        message = "Expected an optimal or incumbent solution status"
        raise ValueError(message)
    fingerprint = data.get("formulation_fingerprint")
    if not isinstance(fingerprint, str) or not fullmatch(
        r"sha256:[0-9a-f]{64}",
        fingerprint,
    ):
        message = "Invalid solution formulation fingerprint"
        raise ValueError(message)
    _validate_values(data.get("values"), data.get("objective_value"))
    return SolutionRecord(
        format_version=1,
        values=data["values"],
        objective_value=data["objective_value"],
        objective_sense="min",
        status=data["status"],
        formulation_fingerprint=fingerprint,
    )


def write_record(path: Path, record: SolutionRecord) -> None:
    """Replace a solution file only after writing the complete JSON payload."""
    stream = NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    )
    temporary = Path(stream.name)
    try:
        with stream:
            json.dump(
                record, stream, allow_nan=False, sort_keys=True, indent=2
            )
            stream.write("\n")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
