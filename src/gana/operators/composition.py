"""Function Compositions"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..sets.objective import O

if TYPE_CHECKING:
    from ..sets.function import F
    from ..sets.variable import V


def inf(function: F | V) -> O:
    """Minimize the function

    :param function: function to minimize
    :type function: F
    """
    return O(function=function)


def sup(function: F | V) -> O:
    """Maximize the function

    :param function: function to maximize
    :type function: F
    """
    return O(function=-function)
