"""Decorators for functions"""

import logging
import time
from functools import wraps


def once(func):
    """Ensures the function is executed only once"""

    def wrapper(*args, **kwargs):
        if not hasattr(wrapper, "has_run"):
            wrapper.has_run = True
            return func(*args, **kwargs)

    return wrapper


def timer(
    logger: logging.Logger, kind: str = None, with_return=True, level=logging.INFO
):
    """
    Logs execution time and optionally shows a full computation using function arguments and result.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            # returns the result if successful, else False
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            if result:
                if kind == 'generate-mps':
                    _return = False
                    msg = f"📝  Generated {result}.mps"

                if kind == 'generate-solution':
                    msg = f"📝  Generated Solution object for {result}. See .solution"

                if kind == 'generate-ppopt':
                    msg = "📝  Generated MPLP. See .formulation"

                if kind == 'generate-gurobi':
                    msg = "📝  Generated gurobipy model. See .formulation"

                if kind == 'solve-mpqp':
                    msg = "✅  Solved MPLP using PPOPT. See .solution"

                if kind == 'optimize':
                    msg = f"✅  {result[0]} optimized using {result[1]}. Display using .output()"

                logger.log(
                    level,
                    f"{msg:<75} ⏱ {elapsed:.4f} s",
                )

            if with_return:
                return result

        return wrapper

    return decorator
