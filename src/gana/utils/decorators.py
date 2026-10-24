"""Decorators for functions"""

import logging
import time
from functools import wraps
from typing import Protocol, cast


class _OnceState(Protocol):
    """The marker installed on a wrapper only after its first invocation."""

    has_run: bool


def once(func):
    """Ensures the function is executed only once"""

    def wrapper(*args, **kwargs):
        """Invoke the function once and return None on subsequent calls."""
        if not hasattr(wrapper, "has_run"):
            cast(_OnceState, wrapper).has_run = True
            return func(*args, **kwargs)
        return None

    return wrapper


def _timer_message(kind: str | None, result) -> str:
    """Build the existing success message independently of timing policy.

    Unsupported kinds retain their historical UnboundLocalError for truthy
    results. The wrapper skips message construction for falsey results.
    """
    if kind == "generate-mps":
        msg = f"📝  Generated {result}.mps"
    if kind == "generate-solution":
        msg = f"📝  Generated Solution object for {result}. See .solution"
    if kind == "generate-ppopt":
        msg = "📝  Generated MPLP. See .formulation"
    if kind == "generate-gurobi":
        msg = "📝  Generated gurobipy model. See .formulation"
    if kind == "solve-mpqp":
        msg = "✅  Solved MPLP using PPOPT. See .solution"
    if kind == "optimize":
        msg = (
            f"✅  {result[0]} optimized using {result[1]}. "
            "Display using .output()"
        )
    return msg


def timer(
    logger: logging.Logger,
    kind: str | None = None,
    with_return=True,
    level=logging.INFO,
):
    """
    Logs execution time and optionally shows a full computation using function
    arguments and result.
    """

    def decorator(func):
        """Wrap a function with timing and the selected return policy."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            """Log successful calls; return their result only when enabled."""
            start = time.time()
            # returns the result if successful, else False
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            if result:
                msg = _timer_message(kind, result)
                logger.log(
                    level,
                    f"{msg:<75} ⏱ {elapsed:.4f} s",
                )

            if with_return:
                return result
            return None

        return wrapper

    return decorator
