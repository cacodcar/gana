"""Function Compositions"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..sets.objective import O

if TYPE_CHECKING:
    from ..sets.function import F
    from ..sets.variable import V


def inf(function: F | V) -> O:
    """Minimize a scalar function; reduce indexed expressions explicitly.

    For example, ``inf(sigma(p.x))`` minimizes the sum of a variable set.
    A function with multiple result rows raises ``ValueError``.

    :param function: function to minimize
    :type function: F
    """
    return O(function=function)


def sup(function: F | V) -> O:
    """Maximize a scalar function by minimizing its negative.

    Indexed expressions require explicit reduction, as with :func:`inf`.
    Objective coefficients and reported values retain Gana's canonical
    minimization sign, including the constant offset.

    :param function: function to maximize
    :type function: F
    """
    return O(function=-function)
