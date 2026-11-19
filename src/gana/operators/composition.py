"""Function Compositions"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..sets.objective import O

if TYPE_CHECKING:
    from ..sets.function import F
    from ..sets.variable import V


def inf(function: F | V) -> O:
    """
    Minimize a scalar function.

    A function with multiple result rows raises ``ValueError``.

    :param function: function to minimize
    :type function: F | V

    .. admonition:: Example

        .. code-block:: python

            from gana import I, P, Prg, V, inf, sigma

            p = Prg()
            p.plants = I("north", "south")
            p.output = V(p.plants)
            p.cost = P(p.plants, _=[3, 7])
            p.objective = inf(sigma(p.cost * p.output))
            assert p.C == [3, 7]
    """
    return O(function=function)


def sup(function: F | V) -> O:
    """
    Maximize a scalar function by minimizing its negative.

    Indexed expressions require explicit reduction, as with :func:`inf`.
    Objective coefficients and reported values retain Gana's canonical
    minimization sign, including the constant offset.

    :param function: function to maximize
    :type function: F | V

    .. admonition:: Example

        .. code-block:: python

            from gana import Prg, V, sup

            p = Prg()
            p.sales = V()
            p.profit = sup(4 * p.sales - 5)
            # The equivalent minimization objective is -4*sales + 5.
            assert p.C == [-4]
            assert p.profit.constant == 5
    """
    return O(function=-function)
