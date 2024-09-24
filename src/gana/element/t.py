"""Parametric variable
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sympy import IndexedBase


@dataclass
class T:
    """Parametric variable"""

    name: str = 't'

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)
