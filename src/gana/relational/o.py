"""Objective"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .f import F


class O:
    """Minimization Objective"""

    def __init__(self, *args: F, name: str = 'min'):
        self.func: F = args[0] if args else None
        self.name = name

        # keeps a count of, updated in program
        self.count: int = None

    @property
    def sym(self):
        """symbolic representation"""
        if self.func:
            return self.func.sym

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)
