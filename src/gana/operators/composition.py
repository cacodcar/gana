"""Function Compositions"""

from ..sets.function import F
from ..sets.objective import O


def inf(function: F) -> F:
    """Minimize the function"""
    return O(function=function)


def sup(function: F) -> F:
    """Maximize the function"""
    return O(function=-function)
