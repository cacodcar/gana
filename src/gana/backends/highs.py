"""HiGHS adapter for Gana's deterministic MPS formulation."""

from pathlib import Path
from tempfile import TemporaryDirectory

from highspy import Highs, HighsModelStatus, HighsStatus, SolutionStatus


def build(program, snapshot) -> Highs:
    """Read the existing MPS representation using a private per-solve path."""
    model = Highs()
    with TemporaryDirectory() as directory:
        stem = str(Path(directory) / "program")
        if snapshot is None:
            program.mps(stem)
        else:
            program._write_native_mps(snapshot, stem)
        if model.readModel(f"{stem}.mps") == HighsStatus.kError:
            message = "HiGHS could not read the exported Gana formulation"
            raise ValueError(message)
    return model


def optimize(model: Highs):
    """Collect named primal values only when HiGHS has a feasible solution."""
    if model.run() == HighsStatus.kError:
        message = "HiGHS failed to solve the formulation"
        raise RuntimeError(message)
    status = model.getModelStatus()
    lp = model.getLp()
    if status == HighsModelStatus.kModelEmpty:
        # HiGHS reports an empty model even for a contradictory constant row.
        if all(lo <= 0 <= hi for lo, hi in zip(lp.row_lower_, lp.row_upper_)):
            return {}, lp.offset_, True
        return None
    if status in (
        HighsModelStatus.kInfeasible,
        HighsModelStatus.kUnbounded,
        HighsModelStatus.kUnboundedOrInfeasible,
    ):
        return None
    solution = model.getSolution()
    feasible = SolutionStatus.kSolutionStatusFeasible
    if (
        not solution.value_valid
        or model.getInfo().primal_solution_status != feasible
    ):
        return None
    values = dict(zip(lp.col_names_, solution.col_value, strict=True))
    return (
        values,
        model.getObjectiveValue(),
        status == HighsModelStatus.kOptimal,
    )
