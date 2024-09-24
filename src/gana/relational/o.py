"""Objective"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .f import F


class O:
    """Minimization Objective"""

    def __init__(self, name: str = 'min', function: F = None):
        self.name = name
        self.function = function
