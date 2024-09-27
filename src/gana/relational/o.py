"""Objective"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .f import F


class O:
    """Minimization Objective"""

    def __init__(self, *args: tuple[F], name: str = 'min'):
        self.func: F = args[0] if args else None
        self.name = name

        # keeps a count of, updated in program
        self.count: int = None

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __len__(self):
        return 1

    def __call__(self):
        """symbolic representation"""
        if self.func:
            return self.func()
        else:
            return 0
